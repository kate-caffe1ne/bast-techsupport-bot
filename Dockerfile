FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Обновляем систему и устанавливаем базовые утилиты
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Создаем виртуальное окружение
RUN python -m venv /opt/venv

# Добавляем виртуальное окружение в PATH
ENV PATH="/opt/venv/bin:$PATH"

# Устанавливаем зависимости Python
# Сначала активируем venv, затем устанавливаем зависимости
RUN . /opt/venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Устанавливаем Chromium и все необходимые системные библиотеки для Playwright
RUN playwright install --with-deps chromium

# Копируем исходный код проекта
COPY . .

# Создаем директорию для базы знаний (на случай если она не проброшена снаружи)
RUN mkdir -p knowledge_base

# Указываем команду запуска по умолчанию
CMD ["python", "bast_parser.py"]