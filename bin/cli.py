"""
bin/cli.py — CLI-точка входу для генерації міксу без Telegram.

Запуск:
    python bin/cli.py --demo
    python bin/cli.py --playlist "https://youtube.com/playlist?list=..."
    python bin/cli.py --skip-download --temp data/temp
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Додаємо корінь проєкту до sys.path (щоб працювало з bin/)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import get_config
from src.core.engine import CenturionEngine
from src.core.models import MixSettings


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Centurion Mix — CLI генератор")
    p.add_argument("--playlist",      default=None,        help="URL плейлиста YouTube")
    p.add_argument("--output",        default=None,        help="Шлях до фінального mp3")
    p.add_argument("--temp",          default=None,        help="Тимчасова папка")
    p.add_argument("--bitrate",       default=None,        help="Бітрейт (наприклад 192k)")
    p.add_argument("--duration-sec",  type=float, default=None, help="Тривалість фрагменту (сек)")
    p.add_argument("--skip-download", action="store_true", help="Обробити локальні mp3")
    p.add_argument("--demo",          action="store_true", help="Демо без YouTube")
    return p


def main() -> None:
    cfg = get_config()
    setup_logging(cfg.log_level)
    log = logging.getLogger(__name__)
    args = build_parser().parse_args()

    if not args.demo and not args.skip_download and not (args.playlist or cfg.playlist_url):
        log.error("Не вказано URL плейлиста. Додай --playlist або PLAYLIST_URL у .env")
        sys.exit(1)

    settings = MixSettings(
        playlist_url=args.playlist or cfg.playlist_url,
        beep_path=cfg.beep_path,
        temp_dir=Path(args.temp) if args.temp else cfg.temp_dir,
        output_path=Path(args.output) if args.output else cfg.output_path,
        ffmpeg_dir=cfg.ffmpeg_dir,
        bitrate=args.bitrate or cfg.bitrate,
        duration_sec=args.duration_sec or cfg.duration_sec,
        beep_gain_db=cfg.beep_gain_db,
    )

    result = CenturionEngine(settings).generate_mix(
        skip_download=args.skip_download,
        demo=args.demo,
    )
    log.info("✅ Готово: %s", result)


if __name__ == "__main__":
    main()

