"""
src/core/mixer.py — фінальна склейка треків через ffmpeg concat demuxer.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from src.core.utils import find_ffmpeg

logger = logging.getLogger(__name__)


class Mixer:
    """Склеює оброблені mp3-фрагменти в один фінальний файл."""

    def __init__(self, ffmpeg_dir: Path) -> None:
        self.ffmpeg_dir = ffmpeg_dir

    def concat(
        self,
        processed_files: list[Path],
        output_path: Path,
        bitrate: str = "192k",
    ) -> None:
        """
        Склеює список mp3 в один файл через ffmpeg concat demuxer.

        Args:
            processed_files: впорядкований список оброблених mp3.
            output_path: шлях до фінального mp3.
            bitrate: бітрейт кодування.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        list_file = output_path.with_suffix(".txt")

        lines: list[str] = []
        for path in processed_files:
            safe = str(path.resolve()).replace("\\", "/").replace("'", "'\\''")
            lines.append(f"file '{safe}'")
        list_file.write_text("\n".join(lines), encoding="utf-8")

        # find_ffmpeg шукає: ffmpeg_dir/ffmpeg.exe → ffmpeg_dir/ffmpeg → PATH
        ffmpeg_bin = find_ffmpeg(self.ffmpeg_dir)

        cmd: list[str] = [
            str(ffmpeg_bin),
            "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c:a", "libmp3lame", "-b:a", bitrate,
            str(output_path),
        ]
        logger.debug("ffmpeg concat: %d files → %s", len(processed_files), output_path.name)
        subprocess.run(cmd, check=True)
        list_file.unlink(missing_ok=True)

