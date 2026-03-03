"""
src/core/models.py — dataclass-моделі для ядра генерації.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class MixSettings:
    """
    Іммутабельні налаштування одного завдання генерації міксу.

    Передається у CenturionEngine при кожному запуску,
    що дозволяє різним користувачам бота мати різні налаштування.
    """

    playlist_url: str
    """URL YouTube-плейлиста."""

    beep_path: Path
    """Шлях до beep.mp3."""

    temp_dir: Path
    """Тимчасова папка для сирих треків."""

    output_path: Path
    """Шлях до фінального mp3-файлу."""

    ffmpeg_dir: Path
    """Папка з ffmpeg/ffprobe бінарниками."""

    bitrate: str = "192k"
    """Бітрейт кодування."""

    duration_sec: float = 60.0
    """Тривалість одного фрагменту в секундах."""

    beep_gain_db: float = -10.0
    """Корекція гучності beep-сигналу в дБ."""

    fade_out_ms: int = 1500
    """Тривалість fade out в мілісекундах."""

