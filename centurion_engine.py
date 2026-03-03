"""
centurion_engine.py — ядро генерації Centurion Mix.

Алгоритм (memory-efficient streaming pipeline):
    1) Отримати список відео з плейлиста БЕЗ завантаження медіа
    2) Завантажити один трек
    3) Одразу обробити: обрізати / normalize / fade out / beep
    4) Зберегти оброблений фрагмент
    5) Негайно видалити сирий файл
    6) Повторити для наступного треку
    7) Склеїти всі фрагменти через ffmpeg concat demuxer
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

from pydub import AudioSegment
from pydub.effects import normalize
from pydub.generators import Sine
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Налаштування
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class MixSettings:
    """Іммутабельні налаштування генерації міксу."""

    playlist_url: str
    beep_path: Path
    temp_dir: Path
    output_path: Path
    bitrate: str = "192k"
    duration_sec: float = 60.0
    beep_gain_db: float = -10.0
    fade_out_ms: int = 1500


# ---------------------------------------------------------------------------
# Основний клас-ядро
# ---------------------------------------------------------------------------

class CenturionEngine:
    """
    Потоковий генератор Centurion Mix.

    Використання::

        settings = MixSettings(playlist_url="...", ...)
        engine = CenturionEngine(settings)
        result_path = engine.generate_mix()   # <- готовий mp3

    Повертає абсолютний шлях до фінального файлу, щоб
    Telegram-бот міг одразу відправити його користувачу.
    """

    def __init__(self, settings: MixSettings) -> None:
        self.settings = settings
        self._processed_dir: Path = settings.temp_dir / "processed"

    # ------------------------------------------------------------------
    # Публічний API
    # ------------------------------------------------------------------

    def generate_mix(
        self,
        skip_download: bool = False,
        demo: bool = False,
    ) -> Path:
        """
        Генерує фінальний мікс і повертає абсолютний шлях до файлу.

        Args:
            skip_download: якщо True — пропустити YouTube і обробити
                           локальні mp3 з temp_dir.
            demo: якщо True — синтезувати тестові треки без YouTube.

        Returns:
            Path: абсолютний шлях до готового mp3.

        Raises:
            FileNotFoundError: beep.mp3 не знайдено.
            RuntimeError: ffmpeg відсутній або плейлист порожній.
            ValueError: не вказано URL плейлиста.
        """
        self._require_audioop()
        self._require_ffmpeg()

        self.settings.temp_dir.mkdir(parents=True, exist_ok=True)
        self._processed_dir.mkdir(parents=True, exist_ok=True)

        processed_files: list[Path] = []

        if demo:
            logger.info("Режим DEMO: генерація синтетичних треків без YouTube")
            beep_path, demo_files = self._create_demo_assets(self.settings.temp_dir)
            beep = AudioSegment.from_file(beep_path)
            processed_files = self._process_local_files(demo_files, beep)

        elif skip_download:
            logger.info("Режим SKIP-DOWNLOAD: обробка локальних mp3")
            if not self.settings.beep_path.exists():
                raise FileNotFoundError(f"Біп не знайдено: {self.settings.beep_path}")
            beep = AudioSegment.from_file(self.settings.beep_path)
            local_files = self._list_mp3_files(self.settings.temp_dir)
            if not local_files:
                raise RuntimeError("У temp-папці немає mp3-файлів для обробки.")
            processed_files = self._process_local_files(local_files, beep)

        else:
            if not self.settings.playlist_url:
                raise ValueError("Не вказано URL плейлиста.")
            if not self.settings.beep_path.exists():
                raise FileNotFoundError(f"Біп не знайдено: {self.settings.beep_path}")

            beep = AudioSegment.from_file(self.settings.beep_path)
            entries = list(self._iter_playlist_entries(self.settings.playlist_url))

            if not entries:
                raise RuntimeError("Плейлист не містить доступних відео.")

            logger.info("Знайдено %d відео у плейлисті. Запускаю потоковий pipeline...", len(entries))

            for index, entry in enumerate(entries, start=1):
                title = str(entry.get("title") or f"track_{index:03d}")
                logger.info("[%d/%d] ⬇ Завантаження: %s", index, len(entries), title)

                raw_file = self._download_single_entry(entry, index)
                if raw_file is None:
                    logger.warning("[%d/%d] ⚠ Пропущено: не вдалося завантажити", index, len(entries))
                    continue

                out_name = f"{index:03d}_{self._sanitize_filename(title)}.mp3"
                out_path = self._processed_dir / out_name

                logger.info("[%d/%d] ⚙ Обробка: %s", index, len(entries), title)
                self._process_song(raw_file, beep, out_path, self.settings)
                processed_files.append(out_path)

                self._safe_unlink(raw_file)
                logger.info("[%d/%d] 🗑 Сирий файл видалено", index, len(entries))

        if not processed_files:
            raise RuntimeError("Немає оброблених треків для фінальної склейки.")

        self._concat_with_ffmpeg(processed_files, self.settings.output_path, self.settings.bitrate)
        final = self.settings.output_path.resolve()
        logger.info("🚀 МІКС ГОТОВИЙ: %s", final)
        return final

    # ------------------------------------------------------------------
    # Отримання плейлиста (без завантаження медіа)
    # ------------------------------------------------------------------

    def _iter_playlist_entries(
        self, playlist_url: str
    ) -> Generator[dict[str, Any], None, None]:
        """
        Повертає метадані відео з плейлиста БЕЗ завантаження медіа.

        Args:
            playlist_url: URL YouTube-плейлиста.

        Yields:
            dict: об'єкт entry з yt_dlp (містить 'id', 'title' тощо).
        """
        ydl_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
            "ignoreerrors": True,
            "noplaylist": False,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            entries: list[dict[str, Any]] = (info or {}).get("entries") or []
            for entry in entries:
                if entry and entry.get("id"):
                    yield entry

    # ------------------------------------------------------------------
    # Завантаження одного треку
    # ------------------------------------------------------------------

    def _download_single_entry(
        self, entry: dict[str, Any], index: int
    ) -> Path | None:
        """
        Завантажує один запис плейлиста в mp3.

        Сирий файл кладе в тимчасову підпапку, потім переміщує
        в temp_dir як ``raw_{index:03d}.mp3``.

        Args:
            entry: entry-об'єкт yt_dlp.
            index: порядковий номер для іменування файлу.

        Returns:
            Path до сирого mp3 або None при невдачі.
        """
        video_id = str(entry["id"])
        url = f"https://www.youtube.com/watch?v={video_id}"

        with tempfile.TemporaryDirectory(
            prefix=f"raw_{index:03d}_",
            dir=str(self.settings.temp_dir),
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
            }

            with YoutubeDL(ydl_opts) as ydl:
                status = ydl.download([url])
                if status != 0:
                    return None

            candidates = sorted(raw_dir.glob("*.mp3"))
            if not candidates:
                return None

            raw_target = self.settings.temp_dir / f"raw_{index:03d}.mp3"
            shutil.move(str(candidates[0]), str(raw_target))
            return raw_target

    # ------------------------------------------------------------------
    # Обробка одного треку
    # ------------------------------------------------------------------

    @staticmethod
    def _process_song(
        song_path: Path,
        beep: AudioSegment,
        out_path: Path,
        settings: MixSettings,
    ) -> None:
        """
        Обробляє один трек: обрізання → normalize → fade out → beep → export.

        Args:
            song_path: шлях до сирого mp3.
            beep: AudioSegment з beep-сигналом.
            out_path: куди зберегти результат.
            settings: налаштування міксу.
        """
        duration_ms = int(settings.duration_sec * 1000)

        song: AudioSegment = AudioSegment.from_file(song_path)
        song = normalize(song[:duration_ms])

        fade_start = len(song) - settings.fade_out_ms
        if fade_start > 0:
            song = song[:fade_start] + song[fade_start:].fade_out(settings.fade_out_ms)

        result = song + beep.apply_gain(settings.beep_gain_db)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        result.export(out_path, format="mp3", bitrate=settings.bitrate)

    # ------------------------------------------------------------------
    # Обробка локальних файлів (skip_download / demo)
    # ------------------------------------------------------------------

    def _process_local_files(
        self,
        files: list[Path],
        beep: AudioSegment,
    ) -> list[Path]:
        """
        Обробляє локальні mp3 без завантаження.

        Args:
            files: відсортований список шляхів до mp3.
            beep: AudioSegment з beep-сигналом.

        Returns:
            list[Path]: список оброблених файлів.
        """
        processed: list[Path] = []
        logger.info("Починаю обробку %d файлів...", len(files))
        for idx, song_path in enumerate(files, start=1):
            out_name = f"{idx:03d}_{self._sanitize_filename(song_path.name)}"
            out_path = self._processed_dir / out_name
            self._process_song(song_path, beep, out_path, self.settings)
            processed.append(out_path)
            logger.info("✅ [%d/%d] Оброблено: %s", idx, len(files), song_path.name)
        return processed

    # ------------------------------------------------------------------
    # Склейка через ffmpeg
    # ------------------------------------------------------------------

    @staticmethod
    def _concat_with_ffmpeg(
        processed_files: list[Path],
        output_path: Path,
        bitrate: str,
    ) -> None:
        """
        Склеює оброблені треки в один файл через ffmpeg concat demuxer.

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

        cmd: list[str] = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c:a", "libmp3lame", "-b:a", bitrate,
            str(output_path),
        ]
        logger.debug("ffmpeg команда: %s", " ".join(cmd))
        subprocess.run(cmd, check=True)

    # ------------------------------------------------------------------
    # Demo-режим
    # ------------------------------------------------------------------

    @staticmethod
    def _create_demo_assets(temp_dir: Path) -> tuple[Path, list[Path]]:
        """
        Синтезує тестовий beep і 3 синусоїдальні треки без YouTube.

        Args:
            temp_dir: папка для збереження demo-файлів.

        Returns:
            tuple: (шлях до demo-beep, список demo-треків).
        """
        temp_dir.mkdir(parents=True, exist_ok=True)
        beep_path = temp_dir / "beep_demo.mp3"
        beep = Sine(1000).to_audio_segment(duration=700).apply_gain(-6)
        beep.export(beep_path, format="mp3", bitrate="192k")

        demo_files: list[Path] = []
        for i, freq in enumerate([220, 330, 440], start=1):
            song_path = temp_dir / f"{i:02d}_demo_{freq}hz.mp3"
            Sine(freq).to_audio_segment(duration=65_000).apply_gain(-8).export(
                song_path, format="mp3", bitrate="192k"
            )
            demo_files.append(song_path)

        return beep_path, demo_files

    # ------------------------------------------------------------------
    # Допоміжні методи
    # ------------------------------------------------------------------

    @staticmethod
    def _list_mp3_files(folder: Path) -> list[Path]:
        """Повертає відсортований список mp3-файлів із папки (без підпапок)."""
        return sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() == ".mp3"
        )

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """
        Прибирає символи, небезпечні для імені файлу.

        Args:
            name: оригінальна назва.

        Returns:
            str: очищена назва (без пустого результату).
        """
        cleaned = name.replace("'", "").replace('"', "").replace("＂", "")
        cleaned = "".join(ch for ch in cleaned if ch not in r'<>:"/\|?*')
        return cleaned.strip() or "track.mp3"

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        """Безпечно видаляє файл, не кидає виняток при помилці."""
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Не вдалося видалити %s: %s", path, exc)

    @staticmethod
    def _require_ffmpeg() -> None:
        """Перевіряє наявність ffmpeg у PATH."""
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "ffmpeg не знайдено у PATH. Встанови ffmpeg і додай у PATH."
            )

    @staticmethod
    def _require_audioop() -> None:
        """Перевіряє доступність audioop (Python ≤3.12) або pyaudioop."""
        try:
            import audioop  # noqa: F401
        except ModuleNotFoundError:
            try:
                import pyaudioop  # noqa: F401
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "Модуль audioop/pyaudioop недоступний. "
                    "Використай Python 3.11/3.12 або встанови pyaudioop."
                ) from exc

