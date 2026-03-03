"""
src/core/processor.py — аудіо-обробка одного треку через pydub.

Відповідає за:
  - обрізання треку до потрібної тривалості
  - нормалізацію гучності
  - fade out
  - накладання beep-сигналу
  - експорт у mp3
  - синтез demo-треків (без YouTube)
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydub import AudioSegment
from pydub.effects import normalize
from pydub.generators import Sine

from src.core.models import MixSettings

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Обробник аудіо-фрагментів для Centurion Mix."""

    def __init__(self, settings: MixSettings) -> None:
        self.settings = settings

    def process(
        self,
        song_path: Path,
        beep: AudioSegment,
        out_path: Path,
    ) -> None:
        """
        Повний pipeline обробки одного треку:
        обрізати → normalize → fade out → beep → export mp3.

        Args:
            song_path: шлях до вхідного mp3.
            beep: AudioSegment з beep-сигналом.
            out_path: куди зберегти оброблений файл.
        """
        duration_ms = int(self.settings.duration_sec * 1000)

        song: AudioSegment = AudioSegment.from_file(song_path)
        song = normalize(song[:duration_ms])

        fade_start = len(song) - self.settings.fade_out_ms
        if fade_start > 0:
            song = (
                song[:fade_start]
                + song[fade_start:].fade_out(self.settings.fade_out_ms)
            )

        result = song + beep.apply_gain(self.settings.beep_gain_db)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        result.export(out_path, format="mp3", bitrate=self.settings.bitrate)
        logger.debug("Exported: %s", out_path.name)

    def load_beep(self) -> AudioSegment:
        """
        Завантажує beep.mp3 з налаштованого шляху.

        Returns:
            AudioSegment: beep-сигнал.

        Raises:
            FileNotFoundError: якщо файл не знайдено.
        """
        if not self.settings.beep_path.exists():
            raise FileNotFoundError(
                f"Beep file not found: {self.settings.beep_path}"
            )
        return AudioSegment.from_file(self.settings.beep_path)

    @staticmethod
    def create_demo_assets(temp_dir: Path) -> tuple[Path, list[Path]]:
        """
        Синтезує тестовий beep і 3 синусоїдальні треки без YouTube.

        Args:
            temp_dir: папка для збереження demo-файлів.

        Returns:
            tuple: (шлях до demo-beep, список demo-треків).
        """
        temp_dir.mkdir(parents=True, exist_ok=True)
        beep_path = temp_dir / "beep_demo.mp3"

        Sine(1000).to_audio_segment(duration=700).apply_gain(-6).export(
            beep_path, format="mp3", bitrate="192k"
        )

        demo_files: list[Path] = []
        for i, freq in enumerate([220, 330, 440], start=1):
            song_path = temp_dir / f"{i:02d}_demo_{freq}hz.mp3"
            Sine(freq).to_audio_segment(duration=65_000).apply_gain(-8).export(
                song_path, format="mp3", bitrate="192k"
            )
            demo_files.append(song_path)

        return beep_path, demo_files

