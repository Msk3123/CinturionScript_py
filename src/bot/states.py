"""
src/bot/states.py — FSM-стани для aiogram 3.
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class MixFlow(StatesGroup):
    """Стани основного flow генерації міксу."""

    waiting_for_playlist_url = State()
    """Бот чекає URL плейлиста від користувача."""

    waiting_for_duration = State()
    """Бот чекає тривалість фрагменту (сек)."""

    waiting_for_bitrate = State()
    """Бот чекає бітрейт (128k / 192k / 320k)."""

    generating = State()
    """Мікс зараз генерується — блокуємо повторний запуск."""

