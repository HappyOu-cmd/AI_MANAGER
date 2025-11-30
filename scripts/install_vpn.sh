#!/bin/bash
# Скрипт для установки и настройки OpenVPN на сервере

set -e

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"
VPN_CONFIG_NAME="Belgium_Oostkamp_S8.ovpn"
VPN_CONFIG_FILE="/tmp/other os/Belgium, Oostkamp S8.ovpn"

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

echo "📦 Шаг 1: Установка OpenVPN..."
remote_exec "apt update && apt install -y openvpn"

echo ""
echo "📁 Шаг 2: Создание директории для конфигураций..."
remote_exec "mkdir -p /etc/openvpn/client"

echo ""
echo "📋 Шаг 3: Копирование конфигурации на сервер..."
# Копируем файл конфигурации
remote_copy "$VPN_CONFIG_FILE" "/tmp/${VPN_CONFIG_NAME}"

# Перемещаем в /etc/openvpn/client с безопасным именем
remote_exec "mv /tmp/${VPN_CONFIG_NAME} /etc/openvpn/client/${VPN_CONFIG_NAME}"

# Устанавливаем правильные права
remote_exec "chmod 600 /etc/openvpn/client/${VPN_CONFIG_NAME}"
remote_exec "chown root:root /etc/openvpn/client/${VPN_CONFIG_NAME}"

echo ""
echo "🔍 Шаг 4: Проверка конфигурации..."
remote_exec "ls -la /etc/openvpn/client/${VPN_CONFIG_NAME}"

echo ""
echo "⚙️  Шаг 5: Создание systemd сервиса для автозапуска..."
# Создаем systemd unit файл
remote_exec "cat > /etc/systemd/system/openvpn-client.service << 'SERVICEEOF'
[Unit]
Description=OpenVPN Client Connection
After=network.target

[Service]
Type=simple
ExecStart=/usr/sbin/openvpn --config /etc/openvpn/client/${VPN_CONFIG_NAME}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF
"

remote_exec "systemctl daemon-reload"
remote_exec "systemctl enable openvpn-client"

echo ""
echo "✅ Установка завершена!"
echo ""
echo "📝 Управление VPN:"
echo "   Запуск:   sudo systemctl start openvpn-client"
echo "   Остановка: sudo systemctl stop openvpn-client"
echo "   Статус:   sudo systemctl status openvpn-client"
echo "   Логи:     sudo journalctl -u openvpn-client -f"
echo ""
echo "🔍 Проверка подключения:"
echo "   ip addr show tun0  # Проверить интерфейс VPN"
echo "   curl ifconfig.me  # Проверить внешний IP"
echo ""
echo "⚠️  Важно:"
echo "   - VPN будет запускаться автоматически при загрузке сервера"
echo "   - Для ручного запуска: sudo systemctl start openvpn-client"
echo "   - Для проверки статуса: sudo systemctl status openvpn-client"

