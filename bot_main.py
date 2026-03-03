"""
bot_main.py — точка входу Telegram-бота Centurion Mix.

Запуск:
    python bot_main.py

Бот стартує через long-polling (підходить для локальної розробки і VPS).
Для продакшену можна перейти на webhook — див. коментар у коді.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import router
from config import load_config


def setup_logging(level: str) -> None:
    """Налаштовує root-логер для консолі / Docker."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def main() -> None:
    """
    Ініціалізує бота та запускає polling.

    Конфіг читається з .env / ENV.
    AppConfig передається у всі handlers через middleware-data.
    """
    cfg = load_config()
    setup_logging(cfg.log_level)
    log = logging.getLogger(__name__)

    # Гарантуємо наявність тимчасових папок
    cfg.temp_dir.mkdir(parents=True, exist_ok=True)
    (cfg.temp_dir / "processed").mkdir(parents=True, exist_ok=True)
    cfg.output_path.parent.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------------------
    # Ініціалізація бота та диспетчера
    # ---------------------------------------------------------------------------
    bot = Bot(
        token=cfg.tg_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # MemoryStorage — зберігає FSM-стани в пам'яті.
    # Для продакшену замінити на RedisStorage:
    #   from aiogram.fsm.storage.redis import RedisStorage
    #   storage = RedisStorage.from_url("redis://localhost:6379")
    storage = MemoryStorage()

    dp = Dispatcher(storage=storage)

    # ---------------------------------------------------------------------------
    # Передаємо AppConfig у всі handlers через workflow_data
    # (доступно як параметр cfg: AppConfig у будь-якому handler)
    # ---------------------------------------------------------------------------
    dp["cfg"] = cfg

    # Реєструємо router з handlers
    dp.include_router(router)

    # ---------------------------------------------------------------------------
    # Запуск
    # ---------------------------------------------------------------------------
    log.info("🤖 Centurion Mix Bot запущено. Очікую повідомлення...")
    log.info("   temp_dir   : %s", cfg.temp_dir.resolve())
    log.info("   output_path: %s", cfg.output_path.resolve())
    log.info("   playlist   : %s", cfg.playlist_url or "(не вказано, задаєш через бот)")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()
        log.info("🛑 Бот зупинено.")


if __name__ == "__main__":
    asyncio.run(main())

