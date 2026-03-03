# src/bot/handlers/ — пакет handlers
from src.bot.handlers.common import router as common_router
from src.bot.handlers.mix import router as mix_router
from src.bot.handlers.settings import router as settings_router

__all__ = ["common_router", "mix_router", "settings_router"]

