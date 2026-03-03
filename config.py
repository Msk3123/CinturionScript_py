"""
config.py — централізована та безпечна конфігурація застосунку.

Всі секрети (TG_BOT_TOKEN тощо) читаються ВИКЛЮЧНО з файлу .env
або змінних середовища. Жодних хардкод-значень!

Використання::

    from config import load_config
    cfg = load_config()          # <- кине ValueError при відсутньому токені
    print(cfg.tg_bot_token)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Автоматично шукає .env у поточній директорії та вище
load_dotenv()


# ---------------------------------------------------------------------------
# Dataclass конфігурації
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AppConfig:
    """
    Іммутабельна конфігурація застосунку.

    Всі поля заповнюються з ENV / .env через :func:`load_config`.
    """

    # --- Обов'язково (валідується при старті) ---
    tg_bot_token: str
    """Telegram Bot API token. Обов'язковий."""

    # --- YouTube / генерація міксу ---
    playlist_url: str
    """URL YouTube-плейлиста."""

    beep_path: Path
    """Шлях до beep.mp3."""

    temp_dir: Path
    """Тимчасова папка для сирих і оброблених треків."""

    output_path: Path
    """Шлях до фінального mp3."""

    bitrate: str
    """Бітрейт кодування, наприклад '192k'."""

    duration_sec: float
    """Тривалість одного фрагменту в секундах."""

    beep_gain_db: float
    """Корекція гучності beep-сигналу в дБ."""

    # --- Логування ---
    log_level: str
    """Рівень логування: DEBUG / INFO / WARNING / ERROR."""


# ---------------------------------------------------------------------------
# Завантаження та валідація
# ---------------------------------------------------------------------------

def _required_env(name: str) -> str:
    """
    Повертає значення обов'язкової змінної середовища.

    Args:
        name: назва змінної.

    Returns:
        str: непорожнє значення.

    Raises:
        ValueError: якщо змінна відсутня або порожня.
    """
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(
            f"❌ Відсутня обов'язкова змінна середовища: {name}\n"
            f"   Додай її у файл .env або як змінну середовища."
        )
    return value


def load_config() -> AppConfig:
    """
    Завантажує та валідує конфігурацію з ENV / .env.

    Виклик при старті застосунку гарантує, що всі
    обов'язкові секрети присутні ДО будь-якої ініціалізації бота.

    Returns:
        AppConfig: валідована іммутабельна конфігурація.

    Raises:
        ValueError: якщо TG_BOT_TOKEN не встановлено.
    """
    return AppConfig(
        # Security: токен ТІЛЬКИ з середовища
        tg_bot_token=_required_env("TG_BOT_TOKEN"),

        # Опційні параметри з дефолтними значеннями
        playlist_url=os.getenv("PLAYLIST_URL", "").strip(),
        beep_path=Path(os.getenv("BEEP_PATH", "assets/beep.mp3")),
        temp_dir=Path(os.getenv("TEMP_DIR", "temp_songs")),
        output_path=Path(os.getenv("OUTPUT_PATH", "Centurion_Mix_BEST.mp3")),
        bitrate=os.getenv("BITRATE", "192k"),
        duration_sec=float(os.getenv("DURATION_SEC", "60")),
        beep_gain_db=float(os.getenv("BEEP_GAIN_DB", "-10")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )

