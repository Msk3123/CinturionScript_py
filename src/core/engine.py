"""
src/core/engine.py — головний оркестратор генерації Centurion Mix.

Координує Downloader → AudioProcessor → Mixer.
Повертає шлях до готового файлу (Path) — бот одразу відправляє його.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from src.core.downloader import Downloader
from src.core.mixer import Mixer
from src.core.models import MixSettings
from src.core.processor import AudioProcessor
from src.core.utils import require_audioop, require_ffmpeg, safe_unlink, sanitize_filename

logger = logging.getLogger(__name__)


class CenturionEngine:
    """
    Оркестратор генерації Centurion Mix.

    Потоковий pipeline (memory-efficient):
      1. Отримати список entries з плейлиста (без завантаження медіа)
      2. Завантажити один трек
      3. Одразу обробити (normalize / fade out / beep)
      4. Зберегти оброблений фрагмент
      5. Видалити сирий файл
      6. Повторити для наступного
      7. Склеїти всі фрагменти через ffmpeg

    Використання::

        engine = CenturionEngine(settings)
        result: Path = engine.generate_mix()
        # result — абсолютний шлях до готового mp3
    """

    def __init__(self, settings: MixSettings) -> None:
        self.settings = settings
        self._processed_dir = settings.temp_dir / "processed"
        self._downloader = Downloader(settings.temp_dir, settings.ffmpeg_dir)
        self._processor = AudioProcessor(settings)
        self._mixer = Mixer(settings.ffmpeg_dir)

    # ──────────────────────────────────────────────────────────────────────────
    # Публічний API
    # ──────────────────────────────────────────────────────────────────────────

    def generate_mix(
        self,
        skip_download: bool = False,
        demo: bool = False,
    ) -> Path:
        """
        Генерує фінальний мікс і повертає абсолютний шлях.

        Args:
            skip_download: обробити локальні mp3 з temp_dir (без YouTube).
            demo: синтезувати тестові треки без YouTube.

        Returns:
            Path: абсолютний шлях до готового mp3.

        Raises:
            FileNotFoundError: beep.mp3 не знайдено.
            RuntimeError: ffmpeg відсутній або нема треків для обробки.
            ValueError: не вказано URL плейлиста.
        """
        require_audioop()
        require_ffmpeg(self.settings.ffmpeg_dir)

        self.settings.temp_dir.mkdir(parents=True, exist_ok=True)
        self._processed_dir.mkdir(parents=True, exist_ok=True)

        processed_files: list[Path] = []

        if demo:
            logger.info("▶ Режим DEMO: синтез тестових треків")
            processed_files = self._run_demo()

        elif skip_download:
            logger.info("▶ Режим SKIP-DOWNLOAD: обробка локальних mp3")
            processed_files = self._run_local()

        else:
            logger.info("▶ Режим YOUTUBE: потоковий pipeline")
            processed_files = self._run_youtube()

        if not processed_files:
            raise RuntimeError("Немає оброблених треків для фінальної склейки.")

        self._mixer.concat(processed_files, self.settings.output_path, self.settings.bitrate)

        final = self.settings.output_path.resolve()
        logger.info("🚀 МІКС ГОТОВИЙ: %s", final)
        return final

    # ──────────────────────────────────────────────────────────────────────────
    # Приватні режими
    # ──────────────────────────────────────────────────────────────────────────

    def _run_demo(self) -> list[Path]:
        """Demo: синтезує тестові треки і обробляє їх."""
        beep_path, demo_files = AudioProcessor.create_demo_assets(self.settings.temp_dir)
        from pydub import AudioSegment
        beep = AudioSegment.from_file(beep_path)
        return self._process_file_list(demo_files, beep)

    def _run_local(self) -> list[Path]:
        """Skip-download: обробляє локальні mp3 з temp_dir."""
        local_files = sorted(
            p for p in self.settings.temp_dir.iterdir()
            if p.is_file() and p.suffix.lower() == ".mp3"
        )
        if not local_files:
            raise RuntimeError("У temp-папці немає mp3-файлів для обробки.")
        beep = self._processor.load_beep()
        logger.info("Знайдено %d локальних файлів", len(local_files))
        return self._process_file_list(local_files, beep)

    def _run_youtube(self) -> list[Path]:
        """YouTube pipeline: download → process → delete raw → next."""
        if not self.settings.playlist_url:
            raise ValueError("Не вказано URL плейлиста.")

        beep = self._processor.load_beep()
        entries = list(self._downloader.iter_playlist_entries(self.settings.playlist_url))
        if not entries:
            raise RuntimeError("Плейлист не містить доступних відео.")

        logger.info("Знайдено %d відео у плейлисті", len(entries))
        processed: list[Path] = []

        for index, entry in enumerate(entries, start=1):
            title = str(entry.get("title") or f"track_{index:03d}")
            logger.info("[%d/%d] ⬇ Завантаження: %s", index, len(entries), title)

            raw_file = self._downloader.download_single(entry, index)
            if raw_file is None:
                logger.warning("[%d/%d] ⚠ Пропущено: не вдалося завантажити", index, len(entries))
                continue

            out_name = f"{index:03d}_{sanitize_filename(title)}.mp3"
            out_path = self._processed_dir / out_name

            logger.info("[%d/%d] ⚙ Обробка: %s", index, len(entries), title)
            self._processor.process(raw_file, beep, out_path)
            processed.append(out_path)

            safe_unlink(raw_file)
            logger.info("[%d/%d] 🗑 Сирий файл видалено", index, len(entries))

        return processed

    def _process_file_list(self, files: list[Path], beep) -> list[Path]:
        """Обробляє список файлів і повертає список оброблених шляхів."""
        from pydub import AudioSegment
        processed: list[Path] = []
        for idx, song_path in enumerate(files, start=1):
            out_name = f"{idx:03d}_{sanitize_filename(song_path.name)}"
            out_path = self._processed_dir / out_name
            self._processor.process(song_path, beep, out_path)
            processed.append(out_path)
            logger.info("✅ [%d/%d] Оброблено: %s", idx, len(files), song_path.name)
        return processed

