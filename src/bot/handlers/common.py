"""
src/bot/handlers/common.py — /start, /help, Reply-кнопки головного меню.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.keyboards import main_menu_kb, mix_menu_kb, settings_kb
from src.bot.states import MixFlow
from src.config.settings import AppConfig

router = Router(name="common")

# ─────────────────────────────────────────────────────────────────────────────
# Текстові шаблони (редагуй тут)
# ─────────────────────────────────────────────────────────────────────────────

TEXT_WELCOME = (
    "👋 <b>Вітаю у Centurion Mix Bot!</b>\n\n"
    "Я генерую аудіо-мікс з YouTube-плейлиста.\n"
    "Кожен трек завантажується окремо → обробляється → сирий файл видаляється.\n\n"
    "Обери дію нижче 👇"
)

TEXT_HELP = (
    "❓ <b>Довідка</b>\n\n"
    "<b>Команди:</b>\n"
    "/start — головне меню\n"
    "/help  — ця довідка\n\n"
    "<b>Кнопки:</b>\n"
    "▶️ <b>Почати завантаження</b> — завантажити плейлист і згенерувати мікс\n"
    "🧪 <b>Демо-режим</b> — тест без YouTube (3 синтетичні треки)\n"
    "⚙️ <b>Налаштування</b> — URL плейлиста, тривалість, бітрейт\n\n"
    "<b>Інструкція:</b>\n"
    "1. ⚙️ → 🔗 Вказати плейлист → вставити URL\n"
    "2. Опційно: змінити тривалість та бітрейт\n"
    "3. ▶️ Почати завантаження\n"
    "4. Отримати готовий mp3 прямо в чат 🎶"
)


# ─────────────────────────────────────────────────────────────────────────────
# /start  /help
# ─────────────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(TEXT_WELCOME, reply_markup=main_menu_kb())
    await message.answer("Обери дію:", reply_markup=mix_menu_kb())


@router.message(Command("help"))
@router.message(F.text == "❓ Допомога")
async def cmd_help(message: Message) -> None:
    await message.answer(TEXT_HELP)


# ─────────────────────────────────────────────────────────────────────────────
# Reply-кнопки
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == "🎵 Створити мікс")
async def reply_create_mix(message: Message) -> None:
    await message.answer("Обери дію:", reply_markup=mix_menu_kb())


@router.message(F.text == "⚙️ Налаштування")
async def reply_settings(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(
        "⚙️ <b>Налаштування</b>",
        reply_markup=settings_kb(
            duration_sec=float(data.get("duration_sec", 60)),
            bitrate=str(data.get("bitrate", "192k")),
        ),
    )

