"""
bot/handlers.py — всі обробники команд, кнопок і повідомлень.

Структура:
  /start, /help          → базові команди
  Reply-кнопки           → головне меню
  Inline callback_query  → генерація, налаштування, скасування
  FSM                    → введення URL / тривалості / бітрейту
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    Message,
)

from centurion_engine import CenturionEngine, MixSettings
from config import AppConfig

from .keyboards import (
    CB_CANCEL,
    CB_HELP,
    CB_SET_BITRATE,
    CB_SET_DURATION,
    CB_SET_PLAYLIST,
    CB_SETTINGS,
    CB_START_DEMO,
    CB_START_MIX,
    CB_STATUS,
    cancel_keyboard,
    main_menu_keyboard,
    mix_menu_keyboard,
    settings_keyboard,
    status_keyboard,
)
from .states import MixFlow

logger = logging.getLogger(__name__)
router = Router(name="centurion")

# ---------------------------------------------------------------------------
# Текстові шаблони (редагуй тут, не торкаючись логіки)
# ---------------------------------------------------------------------------

TEXT_WELCOME = (
    "👋 <b>Вітаю у Centurion Mix Bot!</b>\n\n"
    "Я генерую аудіо-мікс з YouTube-плейлиста.\n"
    "Кожен трек обробляється окремо: обрізається, нормалізується та склеюється в єдиний мікс.\n\n"
    "Обери дію нижче 👇"
)

TEXT_HELP = (
    "❓ <b>Довідка</b>\n\n"
    "<b>Основні команди:</b>\n"
    "/start — головне меню\n"
    "/help  — ця довідка\n\n"
    "<b>Кнопки меню:</b>\n"
    "▶️ <b>Почати завантаження</b> — завантажити плейлист і згенерувати мікс\n"
    "🧪 <b>Демо-режим</b> — тест без YouTube (3 синтетичні треки)\n"
    "⚙️ <b>Налаштування</b> — змінити URL плейлиста, тривалість, бітрейт\n\n"
    "<b>Як використовувати:</b>\n"
    "1. Натисни ⚙️ та вкажи URL плейлиста\n"
    "2. Налаштуй тривалість фрагменту (за замовч. 60 сек)\n"
    "3. Натисни ▶️ <b>Почати завантаження</b>\n"
    "4. Отримай готовий mp3 прямо в чат 🎶"
)

TEXT_GENERATING = (
    "⏳ <b>Генерація міксу запущена...</b>\n\n"
    "Це може зайняти кілька хвилин залежно від розміру плейлиста.\n"
    "Я надішлю файл, як тільки буде готово 🎵"
)

TEXT_ALREADY_RUNNING = (
    "⚠️ Генерація вже виконується.\n"
    "Зачекай або скасуй поточне завдання."
)


# ---------------------------------------------------------------------------
# Хелпер: побудувати MixSettings із FSM-даних або дефолтів конфігу
# ---------------------------------------------------------------------------

def _build_settings(cfg: AppConfig, fsm_data: dict) -> MixSettings:
    """
    Збирає MixSettings із конфігу + FSM-даних користувача.
    FSM-значення мають пріоритет над конфігом.
    """
    return MixSettings(
        playlist_url=fsm_data.get("playlist_url") or cfg.playlist_url,
        beep_path=cfg.beep_path,
        temp_dir=cfg.temp_dir,
        output_path=cfg.output_path,
        bitrate=fsm_data.get("bitrate") or cfg.bitrate,
        duration_sec=float(fsm_data.get("duration_sec") or cfg.duration_sec),
        beep_gain_db=cfg.beep_gain_db,
    )


# ---------------------------------------------------------------------------
# /start та /help
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обробник /start — показує головне меню."""
    await state.clear()
    await message.answer(TEXT_WELCOME, reply_markup=main_menu_keyboard(), parse_mode="HTML")
    await message.answer("Обери дію:", reply_markup=mix_menu_keyboard())


@router.message(Command("help"))
@router.message(F.text == "❓ Допомога")
async def cmd_help(message: Message) -> None:
    """Обробник /help та Reply-кнопки Допомога."""
    await message.answer(TEXT_HELP, parse_mode="HTML")


# ---------------------------------------------------------------------------
# Reply-кнопки головного меню
# ---------------------------------------------------------------------------

@router.message(F.text == "🎵 Створити мікс")
async def reply_create_mix(message: Message) -> None:
    """Reply-кнопка 'Створити мікс' → показує inline-меню."""
    await message.answer("Обери дію:", reply_markup=mix_menu_keyboard())


@router.message(F.text == "🧪 Демо-режим")
async def reply_demo(message: Message, state: FSMContext, bot: Bot, cfg: AppConfig) -> None:
    """Reply-кнопка 'Демо-режим' → одразу запускає demo."""
    await _run_mix(message, state, bot, cfg, demo=True)


@router.message(F.text == "⚙️ Налаштування")
async def reply_settings(message: Message, state: FSMContext) -> None:
    """Reply-кнопка 'Налаштування'."""
    data = await state.get_data()
    await message.answer(
        "⚙️ <b>Налаштування</b>",
        reply_markup=settings_keyboard(
            duration_sec=float(data.get("duration_sec", 60)),
            bitrate=str(data.get("bitrate", "192k")),
        ),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Inline callbacks — запуск міксу
# ---------------------------------------------------------------------------

@router.callback_query(F.data == CB_START_MIX)
async def cb_start_mix(call: CallbackQuery, state: FSMContext, bot: Bot, cfg: AppConfig) -> None:
    """Inline-кнопка ▶️ Почати завантаження."""
    await call.answer()
    await _run_mix(call.message, state, bot, cfg, demo=False)


@router.callback_query(F.data == CB_START_DEMO)
async def cb_start_demo(call: CallbackQuery, state: FSMContext, bot: Bot, cfg: AppConfig) -> None:
    """Inline-кнопка 🧪 Демо без YouTube."""
    await call.answer()
    await _run_mix(call.message, state, bot, cfg, demo=True)


async def _run_mix(
    message: Message,
    state: FSMContext,
    bot: Bot,
    cfg: AppConfig,
    demo: bool = False,
) -> None:
    """
    Внутрішній хелпер запуску генерації міксу.
    Блокує повторний запуск через FSM-стан generating.
    """
    current_state = await state.get_state()
    if current_state == MixFlow.generating:
        await message.answer(TEXT_ALREADY_RUNNING, reply_markup=status_keyboard())
        return

    fsm_data = await state.get_data()

    # Якщо не demo і плейлист не вказаний — просимо ввести
    if not demo and not (fsm_data.get("playlist_url") or cfg.playlist_url):
        await message.answer(
            "🔗 Спочатку вкажи URL плейлиста.\n"
            "Натисни <b>🔗 Вказати плейлист</b> або відправ URL прямо в чат.",
            reply_markup=mix_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.set_state(MixFlow.generating)
    status_msg = await message.answer(TEXT_GENERATING, reply_markup=cancel_keyboard(), parse_mode="HTML")

    settings = _build_settings(cfg, fsm_data)
    engine = CenturionEngine(settings)

    try:
        result_path: Path = await asyncio.to_thread(
            engine.generate_mix,
            False,   # skip_download
            demo,    # demo
        )
    except Exception as exc:
        logger.exception("Помилка генерації: %s", exc)
        await status_msg.edit_text(f"❌ <b>Помилка генерації:</b>\n<code>{exc}</code>", parse_mode="HTML")
        await state.clear()
        return

    await state.clear()

    # Відправляємо файл
    await status_msg.edit_text("✅ <b>Мікс готовий! Відправляю файл...</b>", parse_mode="HTML")
    try:
        audio = FSInputFile(result_path, filename=result_path.name)
        await bot.send_audio(
            chat_id=message.chat.id,
            audio=audio,
            title="Centurion Mix",
            performer="Centurion Bot",
            caption="🎶 Твій мікс готовий!",
        )
    except Exception as exc:
        logger.exception("Не вдалося відправити аудіо: %s", exc)
        await message.answer(f"⚠️ Файл згенеровано, але відправити не вдалося:\n<code>{exc}</code>", parse_mode="HTML")


# ---------------------------------------------------------------------------
# Inline callbacks — скасування
# ---------------------------------------------------------------------------

@router.callback_query(F.data == CB_CANCEL)
async def cb_cancel(call: CallbackQuery, state: FSMContext) -> None:
    """Inline-кнопка 🛑 Скасувати."""
    await call.answer("Скасовую...")
    await state.clear()
    await call.message.edit_text("🛑 <b>Завдання скасовано.</b>", parse_mode="HTML")
    await call.message.answer("Головне меню:", reply_markup=mix_menu_keyboard())


# ---------------------------------------------------------------------------
# Inline callbacks — статус
# ---------------------------------------------------------------------------

@router.callback_query(F.data == CB_STATUS)
async def cb_status(call: CallbackQuery, state: FSMContext) -> None:
    """Inline-кнопка 🔄 Оновити статус."""
    await call.answer()
    current = await state.get_state()
    if current == MixFlow.generating:
        await call.message.edit_text(
            "⏳ <b>Генерація ще виконується...</b>",
            reply_markup=status_keyboard(),
            parse_mode="HTML",
        )
    else:
        await call.message.edit_text(
            "✅ <b>Завдань немає.</b> Можеш запускати новий мікс.",
            reply_markup=mix_menu_keyboard(),
            parse_mode="HTML",
        )


# ---------------------------------------------------------------------------
# Inline callbacks — налаштування
# ---------------------------------------------------------------------------

@router.callback_query(F.data == CB_SETTINGS)
async def cb_settings(call: CallbackQuery, state: FSMContext) -> None:
    """Inline-кнопка ⚙️ Налаштування."""
    await call.answer()
    data = await state.get_data()
    await call.message.edit_text(
        "⚙️ <b>Налаштування</b>\n\nОбери параметр для зміни:",
        reply_markup=settings_keyboard(
            duration_sec=float(data.get("duration_sec", 60)),
            bitrate=str(data.get("bitrate", "192k")),
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data == CB_SET_PLAYLIST)
async def cb_set_playlist(call: CallbackQuery, state: FSMContext) -> None:
    """Запит URL плейлиста від користувача."""
    await call.answer()
    await state.set_state(MixFlow.waiting_for_playlist_url)
    await call.message.answer(
        "🔗 <b>Введи URL YouTube-плейлиста:</b>\n\n"
        "Приклад:\n<code>https://www.youtube.com/playlist?list=PLxxxxxxx</code>",
        parse_mode="HTML",
    )


@router.callback_query(F.data == CB_SET_DURATION)
async def cb_set_duration(call: CallbackQuery, state: FSMContext) -> None:
    """Запит нової тривалості фрагменту."""
    await call.answer()
    await state.set_state(MixFlow.waiting_for_duration)
    await call.message.answer(
        "⏱ <b>Введи тривалість одного фрагменту в секундах</b> (ціле число):\n\n"
        "Наприклад: <code>60</code>",
        parse_mode="HTML",
    )


@router.callback_query(F.data == CB_SET_BITRATE)
async def cb_set_bitrate(call: CallbackQuery, state: FSMContext) -> None:
    """Запит нового бітрейту."""
    await call.answer()
    await state.set_state(MixFlow.waiting_for_bitrate)
    await call.message.answer(
        "🎚 <b>Введи бітрейт mp3:</b>\n\n"
        "Доступні значення: <code>128k</code>, <code>192k</code>, <code>320k</code>",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Inline callbacks — довідка
# ---------------------------------------------------------------------------

@router.callback_query(F.data == CB_HELP)
async def cb_help(call: CallbackQuery) -> None:
    """Inline-кнопка ❓ Допомога."""
    await call.answer()
    await call.message.answer(TEXT_HELP, parse_mode="HTML")


# ---------------------------------------------------------------------------
# FSM — введення URL плейлиста
# ---------------------------------------------------------------------------

@router.message(MixFlow.waiting_for_playlist_url)
async def fsm_receive_playlist_url(message: Message, state: FSMContext) -> None:
    """Отримує URL плейлиста від користувача."""
    url = (message.text or "").strip()
    if "youtube.com/playlist" not in url and "youtu.be" not in url:
        await message.answer(
            "⚠️ Схоже, це не YouTube-плейлист.\n"
            "Введи коректний URL, наприклад:\n"
            "<code>https://www.youtube.com/playlist?list=PLxxxxxxx</code>",
            parse_mode="HTML",
        )
        return

    await state.update_data(playlist_url=url)
    await state.clear()   # знімаємо FSM-стан, але дані лишаються

    # Після очистки стану потрібно знову зберегти дані
    await state.update_data(playlist_url=url)

    await message.answer(
        f"✅ <b>Плейлист збережено:</b>\n<code>{url}</code>\n\n"
        f"Тепер можеш натиснути ▶️ <b>Почати завантаження</b>.",
        reply_markup=mix_menu_keyboard(),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# FSM — введення тривалості
# ---------------------------------------------------------------------------

@router.message(MixFlow.waiting_for_duration)
async def fsm_receive_duration(message: Message, state: FSMContext) -> None:
    """Отримує нову тривалість фрагменту."""
    text = (message.text or "").strip()
    try:
        seconds = float(text)
        if not (10 <= seconds <= 600):
            raise ValueError("поза діапазоном")
    except ValueError:
        await message.answer("⚠️ Введи число від 10 до 600 (секунди).")
        return

    await state.update_data(duration_sec=seconds)
    await state.set_state(None)
    await state.update_data(duration_sec=seconds)

    data = await state.get_data()
    await message.answer(
        f"✅ Тривалість встановлено: <b>{int(seconds)} сек</b>",
        reply_markup=settings_keyboard(
            duration_sec=seconds,
            bitrate=str(data.get("bitrate", "192k")),
        ),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# FSM — введення бітрейту
# ---------------------------------------------------------------------------

ALLOWED_BITRATES = {"128k", "192k", "256k", "320k"}

@router.message(MixFlow.waiting_for_bitrate)
async def fsm_receive_bitrate(message: Message, state: FSMContext) -> None:
    """Отримує новий бітрейт."""
    bitrate = (message.text or "").strip().lower()
    if bitrate not in ALLOWED_BITRATES:
        await message.answer(
            f"⚠️ Допустимі значення: {', '.join(sorted(ALLOWED_BITRATES))}"
        )
        return

    await state.update_data(bitrate=bitrate)
    await state.set_state(None)
    await state.update_data(bitrate=bitrate)

    data = await state.get_data()
    await message.answer(
        f"✅ Бітрейт встановлено: <b>{bitrate}</b>",
        reply_markup=settings_keyboard(
            duration_sec=float(data.get("duration_sec", 60)),
            bitrate=bitrate,
        ),
        parse_mode="HTML",
    )

