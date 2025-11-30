#!/bin/bash
# Скрипт для создания systemd сервиса для OpenVPN

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"
VPN_CONFIG="Belgium, Oostkamp S8.ovpn"
VPN_DIR="/etc/openvpn/hideme"
SERVICE_NAME="openvpn-hideme"

echo "⚙️  Создание systemd сервиса для OpenVPN"
echo "========================================"
echo ""

# Функция для выполнения команд на удаленном сервере
remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

echo "📝 Создание systemd unit файла..."
remote_exec "cat > /etc/systemd/system/${SERVICE_NAME}.service << 'EOF'
[Unit]
Description=OpenVPN HideMyName VPN Connection
After=network.target

[Service]
Type=simple
ExecStart=/usr/sbin/openvpn --config ${VPN_DIR}/${VPN_CONFIG}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
"

echo ""
echo "🔄 Перезагрузка systemd..."
remote_exec "systemctl daemon-reload"

echo ""
echo "▶️  Включение автозапуска..."
remote_exec "systemctl enable ${SERVICE_NAME}"

echo ""
echo "🚀 Запуск сервиса..."
remote_exec "systemctl start ${SERVICE_NAME}"
sleep 3

echo ""
echo "✅ Сервис создан и запущен!"
echo ""
echo "📝 Полезные команды:"
echo "   Статус: systemctl status ${SERVICE_NAME}"
echo "   Остановить: systemctl stop ${SERVICE_NAME}"
echo "   Запустить: systemctl start ${SERVICE_NAME}"
echo "   Перезапустить: systemctl restart ${SERVICE_NAME}"
echo "   Логи: journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "📊 Текущий статус:"
remote_exec "systemctl status ${SERVICE_NAME} --no-pager | head -15"

