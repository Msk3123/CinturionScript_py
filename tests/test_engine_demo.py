"""
tests/test_engine_demo.py — smoke-тест ядра у demo-режимі.

Запуск:
    python -m pytest tests/ -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Гарантуємо, що корінь проєкту є у sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("TG_BOT_TOKEN", "test_smoke_token")

from src.config.settings import get_config
from src.core.engine import CenturionEngine
from src.core.models import MixSettings


@pytest.fixture
def demo_settings(tmp_path: Path) -> MixSettings:
    """MixSettings для demo-режиму з тимчасовими директоріями pytest."""
    cfg = get_config()
    return MixSettings(
        playlist_url="",
        beep_path=cfg.beep_path,
        temp_dir=tmp_path / "temp",
        output_path=tmp_path / "output" / "mix.mp3",
        ffmpeg_dir=cfg.ffmpeg_dir,
        bitrate="128k",
        duration_sec=5.0,   # коротко для тесту
    )


def test_demo_generates_file(demo_settings: MixSettings) -> None:
    """Demo-режим має повернути існуючий mp3-файл."""
    engine = CenturionEngine(demo_settings)
    result = engine.generate_mix(demo=True)

    assert result.exists(), f"Файл не знайдено: {result}"
    assert result.suffix == ".mp3"
    assert result.stat().st_size > 0, "Файл порожній"


def test_demo_result_path_is_absolute(demo_settings: MixSettings) -> None:
    """Результат має бути абсолютним шляхом."""
    engine = CenturionEngine(demo_settings)
    result = engine.generate_mix(demo=True)
    assert result.is_absolute()

