"""
script.py — точка входу CLI для Centurion Mix.

Запуск::

    python script.py --playlist "https://youtube.com/playlist?list=..."
    python script.py --demo
    python script.py --skip-download --temp temp_songs

Всі секрети (TG_BOT_TOKEN) беруться з .env або змінних середовища.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from centurion_engine import CenturionEngine, MixSettings
from config import load_config


# ---------------------------------------------------------------------------
# Логування
# ---------------------------------------------------------------------------

def setup_logging(level: str) -> None:
    """
    Налаштовує root-логер для консолі / Docker-контейнера.

    Args:
        level: рядковий рівень логування (DEBUG/INFO/WARNING/ERROR).
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    """Будує та повертає CLI-парсер аргументів."""
    parser = argparse.ArgumentParser(
        description="Centurion Creator: потоковий генератор аудіо-міксів"
    )
    parser.add_argument("--playlist", default=None, help="URL плейлиста YouTube")
    parser.add_argument("--beep", default=None, help="Шлях до beep.mp3")
    parser.add_argument("--temp", default=None, help="Тимчасова папка")
    parser.add_argument("--output", default=None, help="Фінальний mp3")
    parser.add_argument("--bitrate", default=None, help="Бітрейт mp3 (наприклад 192k)")
    parser.add_argument("--duration-sec", type=float, default=None, help="Тривалість фрагменту (сек)")
    parser.add_argument("--beep-gain-db", type=float, default=None, help="Гучність beep (дБ)")
    parser.add_argument("--skip-download", action="store_true", help="Пропустити YouTube, обробити локальні mp3")
    parser.add_argument("--demo", action="store_true", help="Демо-режим: синтетичні треки без YouTube")
    return parser


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Головна функція CLI.

    Завантажує конфіг, накладає CLI-аргументи поверх ENV-значень,
    запускає CenturionEngine і виводить шлях до готового файлу.
    """
    cfg = load_config()
    setup_logging(cfg.log_level)

    log = logging.getLogger(__name__)
    args = build_arg_parser().parse_args()

    # CLI-аргументи мають пріоритет над .env
    playlist_url = args.playlist  if args.playlist  is not None else cfg.playlist_url
    beep_path    = Path(args.beep)   if args.beep     is not None else cfg.beep_path
    temp_dir     = Path(args.temp)   if args.temp     is not None else cfg.temp_dir
    output_path  = Path(args.output) if args.output   is not None else cfg.output_path
    bitrate      = args.bitrate      if args.bitrate  is not None else cfg.bitrate
    duration_sec = args.duration_sec if args.duration_sec is not None else cfg.duration_sec
    beep_gain_db = args.beep_gain_db if args.beep_gain_db is not None else cfg.beep_gain_db

    if not args.demo and not args.skip_download and not playlist_url:
        raise ValueError(
            "Не вказано URL плейлиста. "
            "Встанови PLAYLIST_URL у .env або передай --playlist."
        )

    settings = MixSettings(
        playlist_url=playlist_url,
        beep_path=beep_path,
        temp_dir=temp_dir,
        output_path=output_path,
        bitrate=bitrate,
        duration_sec=duration_sec,
        beep_gain_db=beep_gain_db,
    )

    engine = CenturionEngine(settings)
    result_path = engine.generate_mix(
        skip_download=args.skip_download,
        demo=args.demo,
    )
    log.info("✅ Фінальний файл: %s", result_path)


if __name__ == "__main__":
    main()
