"""
bot/keyboards.py — всі клавіатури та inline-кнопки бота.

Щоб додати нову кнопку:
  1. Додай константу в CallbackData або новий рядок у потрібну клавіатуру.
  2. Зареєструй handler у handlers.py через @router.callback_query(F.data == CB_*).
"""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# ---------------------------------------------------------------------------
# Callback-константи (щоб не плутати рядки по всьому коду)
# ---------------------------------------------------------------------------
CB_START_MIX        = "mix:start"       # Почати генерацію міксу
CB_START_DEMO       = "mix:demo"        # Демо-режим (без YouTube)
CB_SET_PLAYLIST     = "mix:set_playlist"  # Ввести URL плейлиста
CB_SET_DURATION     = "mix:set_duration"  # Змінити тривалість фрагменту
CB_SET_BITRATE      = "mix:set_bitrate"   # Змінити бітрейт
CB_STATUS           = "mix:status"      # Поточний статус завдання
CB_CANCEL           = "mix:cancel"      # Скасувати поточне завдання
CB_HELP             = "misc:help"       # Довідка
CB_SETTINGS         = "misc:settings"   # Меню налаштувань


# ---------------------------------------------------------------------------
# Головне меню (Reply-клавіатура — кнопки під полем вводу)
# ---------------------------------------------------------------------------

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Reply-клавіатура головного меню.
    Завжди видна під полем вводу тексту.
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🎵 Створити мікс"),
        KeyboardButton(text="🧪 Демо-режим"),
    )
    builder.row(
        KeyboardButton(text="⚙️ Налаштування"),
        KeyboardButton(text="❓ Допомога"),
    )
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


# ---------------------------------------------------------------------------
# Inline-меню генерації (з'являється після /start або кнопки "Створити мікс")
# ---------------------------------------------------------------------------

def mix_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Inline-клавіатура запуску генерації міксу.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="▶️ Почати завантаження", callback_data=CB_START_MIX),
    )
    builder.row(
        InlineKeyboardButton(text="🧪 Демо без YouTube",    callback_data=CB_START_DEMO),
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Вказати плейлист",   callback_data=CB_SET_PLAYLIST),
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Налаштування",       callback_data=CB_SETTINGS),
        InlineKeyboardButton(text="❓ Допомога",            callback_data=CB_HELP),
    )
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Inline-меню налаштувань
# ---------------------------------------------------------------------------

def settings_keyboard(duration_sec: float = 60.0, bitrate: str = "192k") -> InlineKeyboardMarkup:
    """
    Inline-клавіатура налаштувань з поточними значеннями.

    Args:
        duration_sec: поточна тривалість фрагменту.
        bitrate: поточний бітрейт.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"⏱ Тривалість: {int(duration_sec)} сек",
            callback_data=CB_SET_DURATION,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🎚 Бітрейт: {bitrate}",
            callback_data=CB_SET_BITRATE,
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=CB_START_MIX),
    )
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Кнопка скасування (під час виконання завдання)
# ---------------------------------------------------------------------------

def cancel_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавіатура з єдиною кнопкою скасування."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛑 Скасувати", callback_data=CB_CANCEL),
    )
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Кнопка перевірки статусу
# ---------------------------------------------------------------------------

def status_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавіатура для перевірки статусу + скасування."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Оновити статус", callback_data=CB_STATUS),
        InlineKeyboardButton(text="🛑 Скасувати",      callback_data=CB_CANCEL),
    )
    return builder.as_markup()

