"""
src/bot/handlers/mix.py — генерація міксу: запуск, скасування, статус.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from src.bot.keyboards import (
    CB_CANCEL, CB_START_DEMO, CB_START_MIX, CB_STATUS,
    cancel_kb, mix_menu_kb, status_kb,
)
from src.bot.states import MixFlow
from src.config.settings import AppConfig
from src.core.engine import CenturionEngine
from src.core.models import MixSettings

logger = logging.getLogger(__name__)
router = Router(name="mix")

# ─────────────────────────────────────────────────────────────────────────────
# Текстові шаблони
# ─────────────────────────────────────────────────────────────────────────────

TEXT_GENERATING = (
    "⏳ <b>Генерація міксу запущена...</b>\n\n"
    "Це займе кілька хвилин залежно від розміру плейлиста.\n"
    "Надішлю файл, як тільки буде готово 🎵"
)
TEXT_ALREADY_RUNNING = (
    "⚠️ Генерація вже виконується.\n"
    "Зачекай або натисни 🛑 Скасувати."
)


# ─────────────────────────────────────────────────────────────────────────────
# Хелпер: зібрати MixSettings із конфігу + FSM-даних
# ─────────────────────────────────────────────────────────────────────────────

def _build_settings(cfg: AppConfig, data: dict) -> MixSettings:
    return MixSettings(
        playlist_url=data.get("playlist_url") or cfg.playlist_url,
        beep_path=cfg.beep_path,
        temp_dir=cfg.temp_dir,
        output_path=cfg.output_path,
        ffmpeg_dir=cfg.ffmpeg_dir,
        bitrate=data.get("bitrate") or cfg.bitrate,
        duration_sec=float(data.get("duration_sec") or cfg.duration_sec),
        beep_gain_db=cfg.beep_gain_db,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Inline callbacks — запуск
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == CB_START_MIX)
async def cb_start_mix(call: CallbackQuery, state: FSMContext, bot: Bot, cfg: AppConfig) -> None:
    await call.answer()
    await _run_mix(call.message, state, bot, cfg, demo=False)


@router.callback_query(F.data == CB_START_DEMO)
async def cb_start_demo(call: CallbackQuery, state: FSMContext, bot: Bot, cfg: AppConfig) -> None:
    await call.answer()
    await _run_mix(call.message, state, bot, cfg, demo=True)


@router.message(F.text == "🧪 Демо-режим")
async def reply_demo(message: Message, state: FSMContext, bot: Bot, cfg: AppConfig) -> None:
    await _run_mix(message, state, bot, cfg, demo=True)


# ─────────────────────────────────────────────────────────────────────────────
# Основний runner
# ─────────────────────────────────────────────────────────────────────────────

async def _run_mix(
    message: Message,
    state: FSMContext,
    bot: Bot,
    cfg: AppConfig,
    demo: bool = False,
) -> None:
    """Запускає генерацію міксу в окремому потоці через asyncio.to_thread."""
    if await state.get_state() == MixFlow.generating:
        await message.answer(TEXT_ALREADY_RUNNING, reply_markup=status_kb())
        return

    data = await state.get_data()

    if not demo and not (data.get("playlist_url") or cfg.playlist_url):
        await message.answer(
            "🔗 Спочатку вкажи URL плейлиста.\n"
            "⚙️ Налаштування → 🔗 Вказати плейлист",
            reply_markup=mix_menu_kb(),
        )
        return

    await state.set_state(MixFlow.generating)
    status_msg = await message.answer(TEXT_GENERATING, reply_markup=cancel_kb())

    settings = _build_settings(cfg, data)
    engine = CenturionEngine(settings)

    try:
        result_path: Path = await asyncio.to_thread(
            engine.generate_mix, False, demo
        )
    except Exception as exc:
        logger.exception("Помилка генерації: %s", exc)
        await status_msg.edit_text(
            f"❌ <b>Помилка генерації:</b>\n<code>{exc}</code>"
        )
        await state.clear()
        return

    await state.clear()
    await status_msg.edit_text("✅ <b>Мікс готовий! Відправляю файл...</b>")

    try:
        await bot.send_audio(
            chat_id=message.chat.id,
            audio=FSInputFile(result_path, filename=result_path.name),
            title="Centurion Mix",
            performer="Centurion Bot",
            caption="🎶 Твій мікс готовий!",
        )
    except Exception as exc:
        logger.exception("Не вдалося відправити аудіо: %s", exc)
        await message.answer(
            f"⚠️ Файл готовий, але відправити не вдалося:\n<code>{exc}</code>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Скасування та статус
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == CB_CANCEL)
async def cb_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer("Скасовую...")
    await state.clear()
    await call.message.edit_text("🛑 <b>Завдання скасовано.</b>")
    await call.message.answer("Головне меню:", reply_markup=mix_menu_kb())


@router.callback_query(F.data == CB_STATUS)
async def cb_status(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    if await state.get_state() == MixFlow.generating:
        await call.message.edit_text(
            "⏳ <b>Генерація ще виконується...</b>",
            reply_markup=status_kb(),
        )
    else:
        await call.message.edit_text(
            "✅ Завдань немає. Можеш запускати новий мікс.",
            reply_markup=mix_menu_kb(),
        )

