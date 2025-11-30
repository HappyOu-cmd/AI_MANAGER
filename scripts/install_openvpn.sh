#!/bin/bash
# Скрипт для установки и настройки OpenVPN на сервере

set -e

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"
VPN_ARCHIVE="/home/robopes_perm/Загрузки/hideme_632006544899195(1).zip"
TEMP_DIR="/tmp/hideme_vpn_install"

echo "🔐 Установка OpenVPN на сервере"
echo "================================"
echo ""

# Функция для выполнения команд на удаленном сервере
remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

# Функция для копирования файлов
remote_copy() {
    sshpass -p "$SSH_PASS" scp -o StrictHostKeyChecking=no "$1" "$SSH_HOST:$2"
}

echo "📦 Шаг 1: Установка OpenVPN на сервере..."
remote_exec "apt update && apt install -y openvpn"

echo ""
echo "📂 Шаг 2: Распаковка архива локально..."
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"
unzip -o -q "$VPN_ARCHIVE" -d "$TEMP_DIR"

echo ""
echo "🔍 Шаг 3: Поиск конфигурационных файлов..."
# Ищем конкретный файл Belgium, Oostkamp S8.ovpn
OVPN_FILE=$(find "$TEMP_DIR" -name "Belgium, Oostkamp S8.ovpn" | head -1)
if [ -z "$OVPN_FILE" ]; then
    echo "⚠️  Файл 'Belgium, Oostkamp S8.ovpn' не найден, ищем любой .ovpn файл..."
    OVPN_FILE=$(find "$TEMP_DIR" -name "*.ovpn" | head -1)
    if [ -z "$OVPN_FILE" ]; then
        echo "❌ Файл .ovpn не найден в архиве!"
        exit 1
    fi
fi

echo "   Найден файл: $OVPN_FILE"

# Находим все связанные файлы (ключи, сертификаты)
VPN_DIR=$(dirname "$OVPN_FILE")
echo "   Директория: $VPN_DIR"

echo ""
echo "📤 Шаг 4: Копирование файлов на сервер..."
# Создаем директорию на сервере
remote_exec "mkdir -p /etc/openvpn/hideme"

# Копируем только нужный файл Belgium, Oostkamp S8.ovpn
cd "$VPN_DIR"
TARGET_FILE="Belgium, Oostkamp S8.ovpn"
if [ -f "$TARGET_FILE" ]; then
    echo "   Копирую: $TARGET_FILE"
    remote_copy "$TARGET_FILE" "/etc/openvpn/hideme/"
else
    echo "   ⚠️  Файл '$TARGET_FILE' не найден, копирую первый доступный .ovpn файл"
    FIRST_OVPN=$(ls -1 *.ovpn 2>/dev/null | head -1)
    if [ -n "$FIRST_OVPN" ]; then
        echo "   Копирую: $FIRST_OVPN"
        remote_copy "$FIRST_OVPN" "/etc/openvpn/hideme/"
        TARGET_FILE="$FIRST_OVPN"
    else
        echo "   ❌ Не найдено ни одного .ovpn файла!"
        exit 1
    fi
fi

echo ""
echo "🔧 Шаг 5: Настройка прав доступа..."
remote_exec "chmod 600 /etc/openvpn/hideme/*.key /etc/openvpn/hideme/*.pem 2>/dev/null || true"
remote_exec "chmod 644 /etc/openvpn/hideme/*.ovpn /etc/openvpn/hideme/*.crt 2>/dev/null || true"
remote_exec "chown root:root /etc/openvpn/hideme/*"

echo ""
echo "📋 Шаг 6: Проверка конфигурации..."
remote_exec "ls -la /etc/openvpn/hideme/"

echo ""
echo "✅ Установка завершена!"
echo ""
echo "📝 Инструкция по подключению:"
echo "   1. Подключитесь к серверу:"
echo "      ssh root@95.81.96.59"
echo ""
echo "   2. Перейдите в директорию:"
echo "      cd /etc/openvpn/hideme"
echo ""
echo "   3. Запустите VPN:"
echo "      openvpn --config '$TARGET_FILE'"
echo ""
echo "   Или для запуска в фоне:"
echo "      nohup openvpn --config '$(basename "$OVPN_FILE")' > /var/log/openvpn.log 2>&1 &"
echo ""
echo "   Или создайте systemd сервис для автозапуска"

# Очистка
rm -rf "$TEMP_DIR"

