"""
src/bot/router.py — збирає всі sub-router в один головний Router.
"""

from __future__ import annotations

from aiogram import Router

from src.bot.handlers import common_router, mix_router, settings_router


def build_router() -> Router:
    """
    Створює та повертає кореневий Router з усіма handlers.

    Порядок включення важливий:
      1. common  — /start, /help, Reply-кнопки
      2. mix     — генерація, скасування, статус
      3. settings — налаштування через FSM
    """
    root = Router(name="root")
    root.include_router(common_router)
    root.include_router(mix_router)
    root.include_router(settings_router)
    return root

