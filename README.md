# Centurion Creator

Короткий конвеєр для плейлистів YouTube: завантаження, обрізка, нормалізація, біп-сигнал і фінальний мікс.

## Вимоги

- Python 3.10+
- `ffmpeg` у PATH

## Швидкий старт

1. Створіть `assets/beep.mp3` (0.5–1 сек).  
2. Встановіть залежності:

```powershell
python -m pip install -r requirements.txt
```

## Запуск

Демо-режим (без YouTube):

```powershell
python script.py --demo
```

З YouTube плейлистом:

```powershell
python script.py --playlist "YOUR_PLAYLIST_URL"
```

## Примітки

- Тимчасові файли зберігаються у `temp_songs`.
- Щоб використати локальні mp3 без завантаження: `--skip-download`.

