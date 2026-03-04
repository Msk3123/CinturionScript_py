# ============================================================
#  Dockerfile — Python 3.12 + ffmpeg (Linux/сервер/Docker)
#
#  Збірка:   docker compose up -d --build
#  Локально: docker build -t centurion-bot .
# ============================================================

FROM python:3.12-slim

# ffmpeg встановлюється через apt — НЕ потрібен ffmpeg.exe з репо
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Спочатку тільки залежності — кешування шару Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Потім весь код
COPY . .

# Створюємо папки наперед (монтуються як volumes)
RUN mkdir -p data/temp data/output assets

CMD ["python", "bot_main.py"]

