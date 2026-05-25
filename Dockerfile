# Используем полный образ Debian, а не slim, чтобы избежать проблем с зависимостями
FROM python:3.11

# Устанавливаем рабочую директорию
WORKDIR /app

# Обновляем систему и устанавливаем базовые утилиты
RUN apt-get update && apt-get install -y \
    curl \
    git \
    # Очищаем кэш apt, чтобы уменьшить размер образа
    && apt-get clean \
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

# Устанавливаем Chromium и все необходимые системные библиотеки для Playwright
# --with-deps надежно работает на полных образах Debian/Ubuntu
RUN playwright install --with-deps chromium

# Копируем исходный код проекта
COPY . .

# Создаем директорию для базы знаний (на случай если она не проброшена снаружи)
RUN mkdir -p knowledge_base

# Указываем команду запуска по умолчанию
CMD ["python", "bast_parser.py"]