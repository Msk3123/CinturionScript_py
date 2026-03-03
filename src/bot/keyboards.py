"""
src/bot/keyboards.py — всі клавіатури та inline-кнопки бота.

Щоб додати нову кнопку:
  1. Додай CB_* константу нижче.
  2. Додай InlineKeyboardButton у потрібну функцію-клавіатуру.
  3. Зареєструй handler у handlers/*.py через @router.callback_query(F.data == CB_*).
"""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# ─────────────────────────────────────────────────────────────────────────────
# Callback-константи
# ─────────────────────────────────────────────────────────────────────────────
CB_START_MIX     = "mix:start"         # Почати генерацію
CB_START_DEMO    = "mix:demo"          # Демо без YouTube
CB_SET_PLAYLIST  = "mix:set_playlist"  # Ввести URL плейлиста
CB_SET_DURATION  = "mix:set_duration"  # Змінити тривалість
CB_SET_BITRATE   = "mix:set_bitrate"   # Змінити бітрейт
CB_STATUS        = "mix:status"        # Поточний статус завдання
CB_CANCEL        = "mix:cancel"        # Скасувати завдання
CB_HELP          = "misc:help"         # Довідка
CB_SETTINGS      = "misc:settings"     # Меню налаштувань


# ─────────────────────────────────────────────────────────────────────────────
# Reply-клавіатура (кнопки під полем вводу, завжди видимі)
# ─────────────────────────────────────────────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    """Головне Reply-меню."""
    b = ReplyKeyboardBuilder()
    b.row(
        KeyboardButton(text="🎵 Створити мікс"),
        KeyboardButton(text="🧪 Демо-режим"),
    )
    b.row(
        KeyboardButton(text="⚙️ Налаштування"),
        KeyboardButton(text="❓ Допомога"),
    )
    return b.as_markup(resize_keyboard=True, one_time_keyboard=False)


# ─────────────────────────────────────────────────────────────────────────────
# Inline-клавіатури
# ─────────────────────────────────────────────────────────────────────────────

def mix_menu_kb() -> InlineKeyboardMarkup:
    """Inline-меню запуску міксу."""
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="▶️ Почати завантаження", callback_data=CB_START_MIX))
    b.row(InlineKeyboardButton(text="🧪 Демо без YouTube",    callback_data=CB_START_DEMO))
    b.row(InlineKeyboardButton(text="🔗 Вказати плейлист",   callback_data=CB_SET_PLAYLIST))
    b.row(
        InlineKeyboardButton(text="⚙️ Налаштування", callback_data=CB_SETTINGS),
        InlineKeyboardButton(text="❓ Допомога",      callback_data=CB_HELP),
    )
    return b.as_markup()


def settings_kb(duration_sec: float = 60.0, bitrate: str = "192k") -> InlineKeyboardMarkup:
    """Inline-меню налаштувань з поточними значеннями."""
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text=f"⏱ Тривалість: {int(duration_sec)} сек",
        callback_data=CB_SET_DURATION,
    ))
    b.row(InlineKeyboardButton(
        text=f"🎚 Бітрейт: {bitrate}",
        callback_data=CB_SET_BITRATE,
    ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data=CB_START_MIX))
    return b.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    """Кнопка скасування поточного завдання."""
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🛑 Скасувати", callback_data=CB_CANCEL))
    return b.as_markup()


def status_kb() -> InlineKeyboardMarkup:
    """Кнопки перевірки статусу + скасування."""
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🔄 Оновити статус", callback_data=CB_STATUS),
        InlineKeyboardButton(text="🛑 Скасувати",      callback_data=CB_CANCEL),
    )
    return b.as_markup()

