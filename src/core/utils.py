"""
src/core/utils.py — утиліти для ядра: перевірки залежностей, файлові хелпери.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def find_ffmpeg(ffmpeg_dir: Path) -> Path:
    """
    Повертає шлях до виконуваного файлу ffmpeg.

    Порядок пошуку:
      1. ffmpeg_dir/ffmpeg.exe  (Windows-бінарник у репо)
      2. ffmpeg_dir/ffmpeg      (Linux-бінарник у репо)
      3. ffmpeg у системному PATH (Linux apt / Mac brew / Docker)

    Returns:
        Path до ffmpeg-бінарника.

    Raises:
        RuntimeError: якщо ffmpeg не знайдено ніде.
    """
    for candidate in (ffmpeg_dir / "ffmpeg.exe", ffmpeg_dir / "ffmpeg"):
        if candidate.exists():
            return candidate
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return Path(system_ffmpeg)
    raise RuntimeError(
        "ffmpeg не знайдено.\n"
        "  • Windows: поклади ffmpeg.exe у папку ffmpeg/\n"
        "  • Linux/Mac: sudo apt install ffmpeg  або  brew install ffmpeg\n"
        "  • Docker: ffmpeg встановлюється автоматично через Dockerfile"
    )


def require_ffmpeg(ffmpeg_dir: Path) -> None:
    """
    Перевіряє наявність ffmpeg (кидає RuntimeError якщо немає).

    Raises:
        RuntimeError: якщо ffmpeg не знайдено.
    """
    find_ffmpeg(ffmpeg_dir)  # кидає сам якщо не знайшов


def require_audioop() -> None:
    """
    Перевіряє доступність audioop (Python ≤3.12) або pyaudioop.

    Raises:
        RuntimeError: якщо жоден модуль не доступний.
    """
    try:
        import audioop  # noqa: F401
    except ModuleNotFoundError:
        try:
            import pyaudioop  # noqa: F401
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Модуль audioop/pyaudioop недоступний.\n"
                "Використай Python 3.11/3.12 або встанови pyaudioop."
            ) from exc


def sanitize_filename(name: str) -> str:
    """
    Очищає рядок для безпечного використання як ім'я файлу.

    Args:
        name: оригінальна назва.

    Returns:
        str: очищена назва (не порожня).
    """
    cleaned = name.replace("'", "").replace('"', "").replace("＂", "")
    cleaned = "".join(ch for ch in cleaned if ch not in r'<>:"/\|?*')
    return cleaned.strip() or "track.mp3"


def safe_unlink(path: Path) -> None:
    """Безпечно видаляє файл, не кидає виняток при помилці."""
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Не вдалося видалити %s: %s", path, exc)

