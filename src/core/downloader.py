"""
src/core/downloader.py — завантаження треків з YouTube через yt_dlp.

Відповідає виключно за:
  - отримання списку entries з плейлиста (без завантаження медіа)
  - завантаження одного треку в mp3
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Generator

from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)


class Downloader:
    """
    Потоковий завантажувач YouTube-аудіо.

    Не завантажує весь плейлист одразу — тільки по одному треку.
    """

    def __init__(self, temp_dir: Path, ffmpeg_dir: Path) -> None:
        """
        Args:
            temp_dir: папка для тимчасових сирих файлів.
            ffmpeg_dir: папка з ffmpeg-бінарниками.
        """
        self.temp_dir = temp_dir
        self.ffmpeg_dir = ffmpeg_dir

    def iter_playlist_entries(
        self, playlist_url: str
    ) -> Generator[dict[str, Any], None, None]:
        """
        Повертає метадані відео з плейлиста БЕЗ завантаження медіа.

        Args:
            playlist_url: URL YouTube-плейлиста.

        Yields:
            dict: entry-об'єкт yt_dlp (містить 'id', 'title' тощо).
        """
        ydl_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
            "ignoreerrors": True,
            "noplaylist": False,
            "ffmpeg_location": str(self.ffmpeg_dir),
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            entries: list[dict[str, Any]] = (info or {}).get("entries") or []
            for entry in entries:
                if entry and entry.get("id"):
                    yield entry

    def download_single(self, entry: dict[str, Any], index: int) -> Path | None:
        """
        Завантажує один запис плейлиста в mp3.

        Алгоритм:
          1) Завантажує у тимчасову підпапку
          2) Переміщує результат у temp_dir як raw_{index:03d}.mp3
          3) Тимчасова підпапка автоматично видаляється

        Args:
            entry: entry-об'єкт yt_dlp.
            index: порядковий номер (для іменування файлу).

        Returns:
            Path до сирого mp3 або None при невдачі.
        """
        video_id = str(entry["id"])
        url = f"https://www.youtube.com/watch?v={video_id}"

        with tempfile.TemporaryDirectory(
            prefix=f"raw_{index:03d}_",
            dir=str(self.temp_dir),
        ) as raw_tmp:
            raw_dir = Path(raw_tmp)
            outtmpl = str(raw_dir / f"{index:03d}.%(ext)s")

            ydl_opts: dict[str, Any] = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
                "noplaylist": True,
                "ffmpeg_location": str(self.ffmpeg_dir),
            }

            with YoutubeDL(ydl_opts) as ydl:
                status = ydl.download([url])
                if status != 0:
                    return None

            candidates = sorted(raw_dir.glob("*.mp3"))
            if not candidates:
                return None

            raw_target = self.temp_dir / f"raw_{index:03d}.mp3"
            shutil.move(str(candidates[0]), str(raw_target))
            return raw_target

