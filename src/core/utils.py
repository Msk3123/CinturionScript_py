"""
src/core/utils.py — утиліти для ядра: перевірки залежностей, файлові хелпери.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def require_ffmpeg(ffmpeg_dir: Path) -> None:
    """
    Перевіряє наявність ffmpeg.

    Шукає спочатку в ffmpeg_dir, потім у PATH.

    Raises:
        RuntimeError: якщо ffmpeg не знайдено.
    """
    local = ffmpeg_dir / "ffmpeg.exe"
    if local.exists():
        return
    if shutil.which("ffmpeg"):
        return
    raise RuntimeError(
        f"ffmpeg не знайдено.\n"
        f"  Поклади ffmpeg.exe у папку: {ffmpeg_dir}\n"
        f"  або встанови ffmpeg і додай у PATH."
    )


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

