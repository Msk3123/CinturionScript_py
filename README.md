# 🎵 Centurion Mix Bot

Telegram-бот, який генерує музичний мікс з YouTube-плейлиста:  
завантажує треки → обрізає → нормалізує гучність → додає beep-сигнал → склеює в один mp3.

---

## 🚀 Запуск

### Варіант A — локально (Windows)

**1. Встановити залежності**
```powershell
pip install -r requirements.txt
```

**2. ffmpeg** — вже є у папці `ffmpeg/`, нічого додатково не потрібно.

**3. Налаштувати `.env`**
```powershell
copy .env.example .env
# відкрий .env і встав свій TG_BOT_TOKEN
```

**4. Запустити**
```powershell
python bot_main.py
```

---

### Варіант B — Docker (Linux / сервер) ✅ рекомендовано

ffmpeg встановлюється автоматично всередині контейнера.

```bash
cp .env.example .env
# відкрий .env і встав свій TG_BOT_TOKEN

docker compose up -d --build
```

Переглянути логи:
```bash
docker compose logs -f
```

Зупинити:
```bash
docker compose down
```

---

### Варіант C — CLI (без Telegram)

```bash
# Демо-режим (без YouTube, синтезує тестові треки)
python bin/cli.py --demo

# З YouTube-плейлистом
python bin/cli.py --playlist "https://youtube.com/playlist?list=..."

# Обробити локальні mp3 без завантаження
python bin/cli.py --skip-download --temp data/temp
```

---

## ⚙️ Змінні середовища (`.env`)

Скопіюй `.env.example` → `.env` і заповни:

| Змінна | Обов'язкова | Дефолт | Опис |
|---|:---:|---|---|
| `TG_BOT_TOKEN` | ✅ | — | Токен від @BotFather |
| `PLAYLIST_URL` | ❌ | `""` | YouTube-плейлист (або задати через бота) |
| `BEEP_PATH` | ❌ | `assets/beep.mp3` | Шлях до beep-сигналу |
| `TEMP_DIR` | ❌ | `data/temp` | Тимчасова папка |
| `OUTPUT_PATH` | ❌ | `data/output/Centurion_Mix_BEST.mp3` | Фінальний файл |
| `FFMPEG_DIR` | ❌ | `ffmpeg` | Папка з ffmpeg (тільки Windows) |
| `BITRATE` | ❌ | `192k` | Бітрейт mp3 |
| `DURATION_SEC` | ❌ | `60` | Секунд на фрагмент |
| `BEEP_GAIN_DB` | ❌ | `-10` | Гучність beep в дБ |
| `LOG_LEVEL` | ❌ | `INFO` | Рівень логів |

---

## 📁 Структура проєкту

```
.
├── bot_main.py          ← єдина точка запуску бота
├── .env.example         ← шаблон змінних середовища
├── .env                 ← твої секрети (НЕ комітити!)
├── Dockerfile           ← образ для Docker (з ffmpeg)
├── docker-compose.yml   ← запуск одною командою
├── requirements.txt     ← Python залежності
│
├── src/
│   ├── config/
│   │   └── settings.py  ← читання .env, AppConfig
│   ├── core/
│   │   ├── engine.py    ← оркестратор pipeline
│   │   ├── downloader.py← завантаження з YouTube (yt-dlp)
│   │   ├── processor.py ← обробка аудіо (pydub)
│   │   ├── mixer.py     ← склейка через ffmpeg
│   │   ├── models.py    ← MixSettings dataclass
│   │   └── utils.py     ← find_ffmpeg, sanitize, тощо
│   └── bot/
│       ├── router.py    ← збирає всі handlers
│       ├── keyboards.py ← кнопки меню
│       ├── states.py    ← FSM стани
│       ├── handlers/    ← common, mix, settings
│       └── middlewares/ ← logging middleware
│
├── assets/
│   └── beep.mp3         ← beep-сигнал між треками
├── ffmpeg/              ← ffmpeg.exe для Windows (ігнорується в Docker)
├── data/
│   ├── temp/            ← тимчасові треки (створюється автоматично)
│   └── output/          ← фінальні міксі
└── tests/               ← тести
```

---

## 🔧 Як ffmpeg вирішується автоматично

| Середовище | Джерело ffmpeg |
|---|---|
| Windows (локально) | `ffmpeg/ffmpeg.exe` з репо |
| Linux / Mac | системний `ffmpeg` (apt / brew) |
| Docker | встановлюється через `apt` у Dockerfile |
