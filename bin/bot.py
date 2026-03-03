"""
bin/bot.py — точка входу Telegram-бота Centurion Mix.

Запуск:
    python bin/bot.py

Long-polling (локальна розробка / VPS).
Для webhook — розкоментуй блок нижче.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Додаємо корінь проєкту до sys.path (щоб працювало і з bin/)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.middlewares.logging_middleware import LoggingMiddleware
from src.bot.router import build_router
from src.config.settings import get_config


def setup_logging(level: str) -> None:
    """Налаштовує root-логер для консолі / Docker."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def main() -> None:
    """Ініціалізує та запускає бота."""
    cfg = get_config()
    setup_logging(cfg.log_level)
    log = logging.getLogger(__name__)

    # Гарантуємо наявність робочих папок
    cfg.temp_dir.mkdir(parents=True, exist_ok=True)
    (cfg.temp_dir / "processed").mkdir(parents=True, exist_ok=True)
    cfg.output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Bot & Dispatcher ──────────────────────────────────────────────────────
    bot = Bot(
        token=cfg.tg_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # MemoryStorage — для локальної розробки.
    # Продакшен → RedisStorage:
    #   from aiogram.fsm.storage.redis import RedisStorage
    #   storage = RedisStorage.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # ── Middleware ────────────────────────────────────────────────────────────
    dp.update.outer_middleware(LoggingMiddleware())

    # ── AppConfig → доступний у всіх handlers як параметр cfg ────────────────
    dp["cfg"] = cfg

    # ── Routers ──────────────────────────────────────────────────────────────
    dp.include_router(build_router())

    # ── Старт ─────────────────────────────────────────────────────────────────
    log.info("🤖 Centurion Mix Bot запущено")
    log.info("   temp_dir   : %s", cfg.temp_dir.resolve())
    log.info("   output_path: %s", cfg.output_path.resolve())
    log.info("   ffmpeg_dir : %s", cfg.ffmpeg_dir.resolve())
    log.info("   playlist   : %s", cfg.playlist_url or "(задається через бот ⚙️)")

    # ── Long-polling ──────────────────────────────────────────────────────────
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        log.info("🛑 Бот зупинено.")

    # ── Webhook (розкоментуй для продакшену) ──────────────────────────────────
    # from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    # from aiohttp import web
    # WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    # await bot.set_webhook(WEBHOOK_URL)
    # app = web.Application()
    # SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    # setup_application(app, dp, bot=bot)
    # web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))


if __name__ == "__main__":
    asyncio.run(main())

