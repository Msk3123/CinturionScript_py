"""
src/config/settings.py — централізована конфігурація застосунку.

Всі секрети читаються ВИКЛЮЧНО з .env або змінних середовища.
Жодних хардкод-значень у коді!

Використання:
    from src.config.settings import get_config
    cfg = get_config()
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Шукає .env від кореня проєкту
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ---------------------------------------------------------------------------
# Базовий шлях проєкту (для Docker-сумісних відносних шляхів)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Dataclass конфігурації
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AppConfig:
    """
    Іммутабельна конфігурація застосунку.
    Заповнюється з ENV / .env через get_config().
    """

    # ── Telegram ─────────────────────────────────────────────────────────────
    tg_bot_token: str
    """Telegram Bot API token. Обов'язковий."""

    # ── YouTube / генерація міксу ─────────────────────────────────────────────
    playlist_url: str
    """URL YouTube-плейлиста (можна задати через бота)."""

    beep_path: Path
    """Шлях до beep.mp3."""

    temp_dir: Path
    """Тимчасова папка для сирих і оброблених треків."""

    output_path: Path
    """Шлях до фінального mp3."""

    ffmpeg_dir: Path
    """Папка з ffmpeg/ffprobe бінарниками."""

    bitrate: str
    """Бітрейт mp3, наприклад '192k'."""

    duration_sec: float
    """Тривалість одного фрагменту (сек)."""

    beep_gain_db: float
    """Корекція гучності beep (дБ)."""

    # ── Логування ─────────────────────────────────────────────────────────────
    log_level: str
    """Рівень логування: DEBUG / INFO / WARNING / ERROR."""


# ---------------------------------------------------------------------------
# Приватний хелпер
# ---------------------------------------------------------------------------

def _required_env(name: str) -> str:
    """
    Повертає обов'язкову змінну середовища або кидає ValueError.

    Args:
        name: назва змінної.

    Raises:
        ValueError: якщо змінна відсутня або порожня.
    """
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(
            f"❌ Відсутня обов'язкова змінна середовища: {name}\n"
            f"   Додай її у файл .env або як змінну середовища.\n"
            f"   Приклад: cp .env.example .env"
        )
    return value


# ---------------------------------------------------------------------------
# Публічний API
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """
    Завантажує та валідує конфігурацію (singleton через lru_cache).

    Returns:
        AppConfig: валідована іммутабельна конфігурація.

    Raises:
        ValueError: якщо TG_BOT_TOKEN не встановлено.
    """
    return AppConfig(
        # Security: токен ТІЛЬКИ з середовища
        tg_bot_token=_required_env("TG_BOT_TOKEN"),

        # Опційні параметри
        playlist_url=os.getenv("PLAYLIST_URL", "").strip(),
        beep_path=BASE_DIR / os.getenv("BEEP_PATH", "assets/beep.mp3"),
        temp_dir=BASE_DIR / os.getenv("TEMP_DIR", "data/temp"),
        output_path=BASE_DIR / os.getenv("OUTPUT_PATH", "data/output/Centurion_Mix_BEST.mp3"),
        ffmpeg_dir=BASE_DIR / os.getenv("FFMPEG_DIR", "ffmpeg"),
        bitrate=os.getenv("BITRATE", "192k"),
        duration_sec=float(os.getenv("DURATION_SEC", "60")),
        beep_gain_db=float(os.getenv("BEEP_GAIN_DB", "-10")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )

