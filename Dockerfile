FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Обновляем систему и устанавливаем базовые утилиты и зависимости для Playwright
RUN apt-get update && apt-get install -y \
    curl \
    git \
    # --- Зависимости для Playwright / Chromium ---
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    # --- Конец зависимостей ---
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Создаем виртуальное окружение
RUN python -m venv /opt/venv

# Добавляем виртуальное окружение в PATH
ENV PATH="/opt/venv/bin:$PATH"

# Устанавливаем зависимости Python
RUN . /opt/venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Устанавливаем ТОЛЬКО браузер, без системных зависимостей, так как мы их уже поставили
RUN playwright install chromium

# Копируем исходный код проекта
COPY . .

# Создаем директорию для базы знаний (на случай если она не проброшена снаружи)
RUN mkdir -p knowledge_base

# Указываем команду запуска по умолчанию
CMD ["python", "bast_parser.py"]