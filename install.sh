#!/bin/bash

# Настройки
REPO_URL="https://github.com/kate-caffe1ne/bast-techsupport-bot"
INSTALL_DIR="/opt/bast-parser"
DOCKER_IMAGE_NAME="bast-parser"
DOCKER_CONTAINER_NAME="bast-parser-app"
EXEC_BIN="/usr/local/bin/bast_parser"

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Требовать права суперпользователя
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Пожалуйста, запустите установку с правами sudo:${NC}"
  echo -e "curl -fsSL ${REPO_URL}/raw/main/install.sh | sudo bash"
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

# Функция для установки unzip
install_unzip() {
    echo -e "${YELLOW}Unzip не установлен. Начинаем автоматическую установку...${NC}"
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y unzip
    elif command -v yum &> /dev/null; then
        yum install -y unzip
    elif command -v dnf &> /dev/null; then
        dnf install -y unzip
    else
        echo -e "${RED}Ошибка: Не удалось определить пакетный менеджер. Пожалуйста, установите 'unzip' вручную.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Unzip успешно установлен!${NC}"
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

# 2. Проверка и установка unzip
if ! command -v unzip &> /dev/null; then
    install_unzip
fi

# 3. Скачивание и распаковка проекта
echo "Создаем директорию $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR" || exit

echo "Скачиваем последнюю версию проекта..."
curl -fsSL "${REPO_URL}/archive/refs/heads/main.zip" -o "bast-parser.zip"

echo "Распаковываем архив (перезаписывая существующие файлы)..."
unzip -o "bast-parser.zip"

# Надежное копирование содержимого из подпапки в корень
echo "Перемещаем файлы проекта в $INSTALL_DIR..."
cp -a bast-techsupport-bot-main/. .

# Очистка
rm -f "bast-parser.zip"
rm -rf "bast-techsupport-bot-main"

# 4. Остановка и удаление старых сервисов
echo "Останавливаем все запущенные сервисы (если они есть)..."
docker compose down

# 5. Сборка Docker-образа
echo "Собираем Docker-образ для парсера..."
docker compose build --no-cache parser

# 6. Создание команды 'bast_parser'
echo "Создаем команду 'bast_parser'..."
cat << 'EOF' > "$EXEC_BIN"
#!/bin/bash

INSTALL_DIR="/opt/bast-parser"
REPO_URL="https://github.com/kate-caffe1ne/bast-techsupport-bot"

# Функция для вывода помощи
show_help() {
    echo "Управление BAST Parser"
    echo "Использование: bast_parser [команда]"
    echo ""
    echo "Команды:"
    echo "  start    Запустить парсер в фоновом режиме (действие по умолчанию)"
    echo "  logs     Показать логи парсера в реальном времени"
    echo "  stop     Остановить парсер"
    echo "  update   Обновить парсер до последней версии"
    echo "  help     Показать это сообщение"
}

# Переходим в директорию проекта, чтобы docker-compose нашел свой конфиг
cd "$INSTALL_DIR" || exit

# Запускаем все команды docker compose с правами sudo
case "$1" in
    start|"")
        echo "Запускаем BAST Parser..."
        sudo docker compose up -d parser
        echo "Парсер запущен в фоновом режиме! Логи: bast_parser logs"
        ;;
    logs)
        echo "Показываем логи (нажмите Ctrl+C для выхода)..."
        sudo docker compose logs -f parser
        ;;
    stop)
        echo "Останавливаем парсер..."
        sudo docker compose down
        echo "Парсер остановлен."
        ;;
    update)
        echo "Запускаем скрипт обновления..."
        curl -fsSL ${REPO_URL}/raw/main/install.sh | sudo bash
        ;;
    help)
        show_help
        ;;
    *)
        echo "Неизвестная команда: $1"
        show_help
        exit 1
        ;;
esac
EOF
chmod +x "$EXEC_BIN"

echo -e "${GREEN}Установка полностью завершена!${NC}"
echo "--------------------------------------------------------"
echo -e "Теперь вы можете управлять парсером с помощью команд:"
echo -e "  ${GREEN}bast_parser start${NC} (или просто ${GREEN}bast_parser${NC})"
echo -e "  ${GREEN}bast_parser logs${NC}"
echo -e "  ${GREEN}bast_parser stop${NC}"
echo -e "  ${GREEN}bast_parser update${NC}"
echo "--------------------------------------------------------"