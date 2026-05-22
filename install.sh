#!/bin/bash

# Настройки
REPO_URL="https://github.com/kate-caffe1ne/bast-techsupport-bot.git"
INSTALL_DIR="/opt/bast-parser"
DOCKER_IMAGE_NAME="bast-parser"
DOCKER_CONTAINER_NAME="bast-parser-app"
EXEC_BIN="/usr/local/bin/bast_parser"

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Требовать права суперпользователя для записи в /opt и /usr/local/bin
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Пожалуйста, запустите установку с правами sudo:${NC}"
  echo -e "sudo bash <(curl -fsSL https://raw.githubusercontent.com/kate-caffe1ne/bast-techsupport-bot/main/install.sh)"
  exit 1
fi

# --- Функции ---

# Функция для установки Docker и Docker Compose
install_docker() {
    echo -e "${YELLOW}Docker не найден. Начинаем автоматическую установку...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh

    systemctl start docker || service docker start
    systemctl enable docker || service docker enable

    echo -e "${GREEN}Docker успешно установлен!${NC}"

    echo -e "${YELLOW}Устанавливаем Docker Compose...${NC}"
    apt-get update
    apt-get install -y docker-compose-plugin || apt-get install -y docker-compose
    echo -e "${GREEN}Docker Compose успешно установлен!${NC}"
}

# Функция для установки Git
install_git() {
    echo -e "${YELLOW}Git не установлен. Начинаем автоматическую установку...${NC}"
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y git
    elif command -v yum &> /dev/null; then
        yum install -y git
    elif command -v dnf &> /dev/null; then
        dnf install -y git
    else
        echo -e "${RED}Ошибка: Не удалось определить пакетный менеджер. Пожалуйста, установите Git вручную.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Git успешно установлен!${NC}"
}

# --- Основной скрипт ---

echo -e "${GREEN}Начинаем установку/обновление BAST Parser...${NC}"

# 1. Проверка и установка Docker и Docker Compose
if ! command -v docker &> /dev/null; then
    install_docker
fi
if ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}Docker Compose не найден. Устанавливаем...${NC}"
    apt-get update
    apt-get install -y docker-compose-plugin || apt-get install -y docker-compose
fi

# 2. Проверка и установка Git
if ! command -v git &> /dev/null; then
    install_git
fi

# 3. Клонирование или обновление репозитория
if [ -d "$INSTALL_DIR" ]; then
    echo "Директория $INSTALL_DIR существует. Обновляем репозиторий..."
    cd "$INSTALL_DIR" || exit
    git stash
    git pull origin main
    git stash pop || true
else
    echo "Клонируем репозиторий в $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR" || exit
fi

# 4. Остановка и удаление старых сервисов, если они запущены
echo "Останавливаем все запущенные сервисы (если они есть)..."
docker compose down

# 5. Сборка Docker-образа
echo "Собираем Docker-образ для парсера..."
docker compose build --no-cache parser

# 6. Создание алиаса (исполняемого файла) для быстрого запуска
echo "Создаем команду 'bast_parser'..."

cat << 'EOF' > "$EXEC_BIN"
#!/bin/bash

INSTALL_DIR="/opt/bast-parser"

echo "Переходим в директорию проекта..."
cd "$INSTALL_DIR" || exit

echo "Запускаем BAST Parser через Docker Compose..."
# -d для фонового режима
# --build чтобы пересобрать образ, если код изменился
docker compose up -d --build parser

echo "Парсер запущен в фоновом режиме!"
echo "----------------------------------------"
echo "Логи можно смотреть командой: docker compose logs -f parser"
echo "Остановить парсер: docker compose down"
echo "Сгенерированные файлы сохраняются в: $INSTALL_DIR/knowledge_base"
EOF

chmod +x "$EXEC_BIN"

echo -e "${GREEN}Установка полностью завершена!${NC}"
echo "--------------------------------------------------------"
echo -e "Теперь вы можете запустить парсер, просто введя команду:"
echo -e "${GREEN}bast_parser${NC}"
echo "--------------------------------------------------------"