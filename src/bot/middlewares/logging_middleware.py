"""
src/bot/middlewares/logging_middleware.py

Логує кожен вхідний update: хто написав, який тип, який текст/callback.
Корисно для debug і моніторингу в Docker.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

logger = logging.getLogger("bot.updates")


class LoggingMiddleware(BaseMiddleware):
    """Логує кожен вхідний Telegram update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Update):
            if event.message:
                m = event.message
                logger.debug(
                    "MSG  user_id=%s name=%s text=%r",
                    m.from_user.id if m.from_user else "?",
                    m.from_user.full_name if m.from_user else "?",
                    (m.text or "")[:80],
                )
            elif event.callback_query:
                cq = event.callback_query
                logger.debug(
                    "CB   user_id=%s data=%r",
                    cq.from_user.id if cq.from_user else "?",
                    cq.data,
                )
        return await handler(event, data)

