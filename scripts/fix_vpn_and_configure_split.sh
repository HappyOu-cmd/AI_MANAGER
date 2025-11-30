#!/bin/bash
# Восстановление VPN конфигурации и настройка split-tunneling для SSH

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"
VPN_CONFIG="/etc/openvpn/client/Belgium_Oostkamp_S8.ovpn"
BACKUP_CONFIG="/etc/openvpn/client/Belgium_Oostkamp_S8.ovpn.backup"
UP_SCRIPT="/etc/openvpn/client/up.sh"
DOWN_SCRIPT="/etc/openvpn/client/down.sh"

echo "🔧 Восстановление VPN и настройка split-tunneling"
echo "=================================================="
echo ""

# Функция для выполнения команд на удаленном сервере
remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

echo "🛑 Шаг 1: Остановка VPN..."
remote_exec "systemctl stop openvpn-client || true"
sleep 2

echo ""
echo "📝 Шаг 2: Восстановление конфигурации из backup..."
remote_exec "cp ${BACKUP_CONFIG} ${VPN_CONFIG}"
remote_exec "chmod 600 ${VPN_CONFIG}"

echo ""
echo "📋 Шаг 3: Создание up скрипта для split-tunneling..."
remote_exec "cat > ${UP_SCRIPT} << 'UPEOF'
#!/bin/bash
# Policy-based routing для исключения SSH из VPN

# Получаем оригинальный шлюз (до VPN)
ORIGINAL_GW=\$(ip route | grep default | grep -v tun0 | awk '{print \$3}' | head -1)
ORIGINAL_IF=\$(ip route | grep default | grep -v tun0 | awk '{print \$5}' | head -1)

if [ -z \"\$ORIGINAL_GW\" ] || [ -z \"\$ORIGINAL_IF\" ]; then
    echo \"Ошибка: не удалось найти оригинальный шлюз\" >> /var/log/openvpn-client.log
    exit 1
fi

# Создаем отдельную таблицу маршрутизации для SSH (таблица 100)
ip route add default via \$ORIGINAL_GW dev \$ORIGINAL_IF table 100 2>/dev/null || true

# Маркируем SSH трафик (порт 22) через iptables
iptables -t mangle -A OUTPUT -p tcp --sport 22 -j MARK --set-mark 1 2>/dev/null || true
iptables -t mangle -A OUTPUT -p tcp --dport 22 -j MARK --set-mark 1 2>/dev/null || true

# Используем таблицу 100 для маркированного трафика (SSH)
ip rule add fwmark 1 table 100 2>/dev/null || true

# Также добавляем правило для локального IP сервера
SERVER_IP=\"95.81.96.59\"
ip route add \$SERVER_IP/32 via \$ORIGINAL_GW dev \$ORIGINAL_IF table 100 2>/dev/null || true
ip rule add from \$SERVER_IP table 100 2>/dev/null || true

echo \"VPN UP: Policy-based routing настроен\" >> /var/log/openvpn-client.log
echo \"Original GW: \$ORIGINAL_GW, Interface: \$ORIGINAL_IF\" >> /var/log/openvpn-client.log
UPEOF
chmod +x ${UP_SCRIPT}
"

echo ""
echo "📋 Шаг 4: Создание down скрипта..."
remote_exec "cat > ${DOWN_SCRIPT} << 'DOWNEOF'
#!/bin/bash
# Очистка policy-based routing при отключении VPN

# Удаляем правила iptables
iptables -t mangle -D OUTPUT -p tcp --sport 22 -j MARK --set-mark 1 2>/dev/null || true
iptables -t mangle -D OUTPUT -p tcp --dport 22 -j MARK --set-mark 1 2>/dev/null || true

# Удаляем правила маршрутизации
ip rule del fwmark 1 table 100 2>/dev/null || true

SERVER_IP=\"95.81.96.59\"
ORIGINAL_GW=\$(ip route | grep default | grep -v tun0 | awk '{print \$3}' | head -1)
ORIGINAL_IF=\$(ip route | grep default | grep -v tun0 | awk '{print \$5}' | head -1)

if [ -n \"\$ORIGINAL_GW\" ] && [ -n \"\$ORIGINAL_IF\" ]; then
    ip route del \$SERVER_IP/32 via \$ORIGINAL_GW dev \$ORIGINAL_IF table 100 2>/dev/null || true
    ip rule del from \$SERVER_IP table 100 2>/dev/null || true
    ip route del default table 100 2>/dev/null || true
fi

echo \"VPN DOWN: Policy-based routing очищен\" >> /var/log/openvpn-client.log
DOWNEOF
chmod +x ${DOWN_SCRIPT}
"

echo ""
echo "⚙️  Шаг 5: Добавление настроек split-tunneling в конфигурацию VPN..."
# Добавляем redirect-gateway и up/down скрипты в конфигурацию
remote_exec "cat >> ${VPN_CONFIG} << 'CONFIGEOF'

# Перенаправляем весь трафик через VPN
redirect-gateway def1

# Скрипты для управления маршрутами (split-tunneling для SSH)
script-security 2
up ${UP_SCRIPT}
down ${DOWN_SCRIPT}
CONFIGEOF
"

echo ""
echo "▶️  Шаг 6: Запуск VPN..."
remote_exec "systemctl start openvpn-client"
sleep 8

echo ""
echo "🔍 Шаг 7: Проверка статуса..."
remote_exec "systemctl status openvpn-client --no-pager | head -15"

echo ""
echo "🌐 Шаг 8: Проверка внешнего IP..."
EXTERNAL_IP=$(sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "curl -s --max-time 5 ifconfig.me 2>&1")
echo "   Внешний IP: $EXTERNAL_IP"

echo ""
echo "✅ Настройка завершена!"
echo ""
echo "📋 Что было сделано:"
echo "   ✓ VPN конфигурация восстановлена из backup"
echo "   ✓ Policy-based routing настроен для SSH"
echo "   ✓ redirect-gateway включен (весь трафик через VPN)"
echo "   ✓ SSH исключен из VPN (порт 22)"
echo ""
echo "🔍 Проверка:"
echo "   - SSH: ssh root@95.81.96.59 (должен работать)"
echo "   - Внешний IP: curl ifconfig.me (должен быть IP VPN, не 95.81.96.59)"
echo "   - Логи: tail -f /var/log/openvpn-client.log"
echo "   - Статус VPN: systemctl status openvpn-client"

