"""
bot/states.py — FSM-стани для діалогів з користувачем.

Aiogram 3 використовує StatesGroup + State для відстеження
кроку діалогу (наприклад, "чекаємо URL від користувача").
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class MixFlow(StatesGroup):
    """Стани основного flow генерації міксу."""

    # Очікуємо URL плейлиста від користувача
    waiting_for_playlist_url = State()

    # Очікуємо нову тривалість фрагменту (у секундах)
    waiting_for_duration = State()

    # Очікуємо новий бітрейт
    waiting_for_bitrate = State()

    # Мікс зараз генерується (блокуємо повторний запуск)
    generating = State()

