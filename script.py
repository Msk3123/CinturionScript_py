import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from pydub import AudioSegment
from pydub.effects import normalize
from pydub.generators import Sine
from yt_dlp import YoutubeDL


DEFAULT_PLAYLIST_URL = ""
DEFAULT_BEEP_PATH = "assets/beep.mp3"
DEFAULT_TEMP_DIR = "temp_songs"
DEFAULT_OUTPUT = "Centurion_Mix_BEST.mp3"
DEFAULT_BITRATE = "192k"
DEFAULT_DURATION_SEC = 60.0
DEFAULT_BEEP_AT_SEC = 59.0
DEFAULT_BEEP_GAIN_DB = -10.0


def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg не знайдено у PATH. Встанови ffmpeg і додай у PATH."
        )


def _download_playlist(playlist_url: str, temp_dir: Path) -> None:
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(temp_dir / "%(playlist_index)02d_%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "noplaylist": False,
        "ignoreerrors": True,   # ← пропускає недоступні відео
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])

def _list_mp3_files(folder: Path) -> list[Path]:
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".mp3"]
    return sorted(files)


def _process_song(
    song_path: Path,
    beep: AudioSegment,
    duration_ms: int,
    beep_at_ms: int,
    beep_gain_db: float,
    out_path: Path,
    bitrate: str,
    fade_out_ms: int = 1500,  # 1.5 секунди fade out перед beep
) -> None:
    song = AudioSegment.from_file(song_path)
    song = song[:duration_ms]
    song = normalize(song)

    # Fade out за 1.5 сек до кінця треку
    fade_start = len(song) - fade_out_ms
    if fade_start > 0:
        # Частина до fade out — без змін
        before_fade = song[:fade_start]
        # Частина з fade out
        fading_part = song[fade_start:].fade_out(fade_out_ms)
        song = before_fade + fading_part

    beep_adj = beep.apply_gain(beep_gain_db)

    # Beep йде ПІСЛЯ треку
    result = song + beep_adj

    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.export(out_path, format="mp3", bitrate=bitrate)


def _concat_with_ffmpeg(processed_files: list[Path], output_path: Path, bitrate: str) -> None:
    list_file = output_path.with_suffix(".txt")
    lines = []
    for path in processed_files:
        safe_path = str(path.resolve()).replace("\\", "/")
        safe_path = safe_path.replace("'", "'\\''")
        lines.append(f"file '{safe_path}'")
    list_file.write_text("\n".join(lines), encoding="utf-8")

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        str(output_path),
    ]
    subprocess.run(cmd, check=True)

def _sanitize_filename(name: str) -> str:
        """Замінює проблемні символи у назві файлу."""
        return name.replace("'", "").replace('"', "").replace("＂", "")

def _create_demo_assets(temp_dir: Path) -> tuple[Path, list[Path]]:
    temp_dir.mkdir(parents=True, exist_ok=True)
    beep_path = temp_dir / "beep_demo.mp3"

    beep = Sine(1000).to_audio_segment(duration=700).apply_gain(-6)
    beep.export(beep_path, format="mp3", bitrate=DEFAULT_BITRATE)

    demo_files = []
    for i, freq in enumerate([220, 330, 440], start=1):
        song_path = temp_dir / f"{i:02d}_demo_{freq}hz.mp3"
        song = Sine(freq).to_audio_segment(duration=65000).apply_gain(-8)
        song.export(song_path, format="mp3", bitrate=DEFAULT_BITRATE)
        demo_files.append(song_path)

    return beep_path, demo_files


def _require_audioop() -> None:
    try:
        import audioop  # noqa: F401
    except ModuleNotFoundError:
        try:
            import pyaudioop  # noqa: F401
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Модуль audioop/pyaudioop недоступний. "
                "Спробуй Python 3.11/3.12 або встанови pyaudioop для цієї версії."
            ) from exc


def run_centurion_pipeline(
    playlist_url: str,
    beep_path: Path,
    temp_dir: Path,
    output_path: Path,
    bitrate: str,
    duration_sec: float,
    beep_at_sec: float,
    beep_gain_db: float,
    skip_download: bool,
    demo: bool,
) -> None:
    _require_audioop()
    _require_ffmpeg()
    temp_dir.mkdir(parents=True, exist_ok=True)

    if demo:
        beep_path, demo_files = _create_demo_assets(temp_dir)
        files = demo_files
    else:
        if not skip_download:
            if not playlist_url:
                raise ValueError("Не вказано URL плейлиста.")
            _download_playlist(playlist_url, temp_dir)
        files = _list_mp3_files(temp_dir)

    if not files:
        raise RuntimeError("У папці немає mp3-файлів для обробки.")

    if not beep_path.exists():
        raise FileNotFoundError(f"Біп не знайдено: {beep_path}")

    beep = AudioSegment.from_file(beep_path)
    duration_ms = int(duration_sec * 1000)
    beep_at_ms = int(beep_at_sec * 1000)

    processed_dir = temp_dir / "processed"
    processed_files = []

    print(f"Починаю обробку {len(files)} пісень...")
    for song_path in files:
        safe_name = _sanitize_filename(song_path.name)
        out_path = processed_dir / safe_name
        _process_song(
            song_path,
            beep,
            duration_ms,
            beep_at_ms,
            beep_gain_db,
            out_path,
            bitrate,
        )
        processed_files.append(out_path)
        print(f"✅ Оброблено: {song_path.name}")

    _concat_with_ffmpeg(processed_files, output_path, bitrate)
    print(f"🚀 МІКС ГОТОВИЙ: {output_path}")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Centurion Creator: конвеєр для плейлистів YouTube"
    )
    parser.add_argument("--playlist", default=DEFAULT_PLAYLIST_URL, help="URL плейлиста")
    parser.add_argument("--beep", default=DEFAULT_BEEP_PATH, help="Шлях до beep.mp3")
    parser.add_argument("--temp", default=DEFAULT_TEMP_DIR, help="Тимчасова папка")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Фінальний mp3 файл")
    parser.add_argument("--bitrate", default=DEFAULT_BITRATE, help="Бітрейт mp3")
    parser.add_argument(
        "--duration-sec",
        type=float,
        default=DEFAULT_DURATION_SEC,
        help="Тривалість фрагменту",
    )
    parser.add_argument(
        "--beep-at-sec",
        type=float,
        default=DEFAULT_BEEP_AT_SEC,
        help="Секунда накладання біпа",
    )
    parser.add_argument(
        "--beep-gain-db",
        type=float,
        default=DEFAULT_BEEP_GAIN_DB,
        help="Корекція гучності біпа (дБ)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Пропустити завантаження і обробити локальні mp3",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Демо-режим без YouTube",
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    run_centurion_pipeline(
        playlist_url=args.playlist,
        beep_path=Path(args.beep),
        temp_dir=Path(args.temp),
        output_path=Path(args.output),
        bitrate=args.bitrate,
        duration_sec=args.duration_sec,
        beep_at_sec=args.beep_at_sec,
        beep_gain_db=args.beep_gain_db,
        skip_download=args.skip_download,
        demo=args.demo,
    )


if __name__ == "__main__":
    main()
