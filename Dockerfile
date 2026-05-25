# Используем официальный Docker-образ от Microsoft для Playwright.
# В нем УЖЕ настроены все системные библиотеки, шрифты, IPC и DBUS,
# необходимые для бесперебойного запуска Chromium в контейнере.
FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python.
# В этом образе можно безопасно ставить пакеты глобально.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# На всякий случай гарантируем установку именно Chromium (обычно он уже там есть)
RUN playwright install chromium

# Копируем исходный код проекта
COPY . .

# Создаем директорию для базы знаний (на случай если она не проброшена снаружи)
RUN mkdir -p knowledge_base

# Указываем команду запуска по умолчанию
CMD ["python", "bast_parser.py"]