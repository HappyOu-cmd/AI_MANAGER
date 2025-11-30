#!/bin/bash
# Правильная настройка VPN: SSH напрямую, остальное через VPN
# Использует policy-based routing с iptables

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"
VPN_CONFIG="/etc/openvpn/client/Belgium_Oostkamp_S8.ovpn"
UP_SCRIPT="/etc/openvpn/client/up.sh"
DOWN_SCRIPT="/etc/openvpn/client/down.sh"

echo "🔧 Правильная настройка VPN с policy-based routing"
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
echo "📝 Шаг 2: Создание резервной копии..."
remote_exec "cp ${VPN_CONFIG} ${VPN_CONFIG}.backup.$(date +%s)"

echo ""
echo "📋 Шаг 3: Создание up скрипта с policy-based routing..."
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

# Получаем VPN шлюз
VPN_GW=\$(ip route | grep default | grep tun0 | awk '{print \$3}' | head -1)

# Создаем отдельную таблицу маршрутизации для SSH (таблица 100)
ip route add default via \$ORIGINAL_GW dev \$ORIGINAL_IF table 100 2>/dev/null || true

# Маркируем SSH трафик (порт 22) через iptables
iptables -t mangle -A OUTPUT -p tcp --sport 22 -j MARK --set-mark 1
iptables -t mangle -A OUTPUT -p tcp --dport 22 -j MARK --set-mark 1

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
echo "⚙️  Шаг 5: Обновление конфигурации VPN с redirect-gateway..."
# Создаем конфигурацию с redirect-gateway и up/down скриптами
remote_exec "cat > ${VPN_CONFIG} << 'VPNEOF'
client

#connect to VPN server
remote 46.183.187.100 53597
proto udp

#socket buffer size
sndbuf 262144
rcvbuf 262144

#DNS server to use
dhcp-option DNS 1.1.1.1

# Перенаправляем весь трафик через VPN
redirect-gateway def1

# Скрипты для управления маршрутами
script-security 2
up ${UP_SCRIPT}
down ${DOWN_SCRIPT}

#certificate-related settings
remote-cert-tls server

#cipher to use
cipher AES-256-CBC

auth-nocache

#use virtual interface 'tun'
dev tun

resolv-retry infinite
nobind
persist-key
persist-tun

verb 4
mute 20

explicit-exit-notify

<ca>
-----BEGIN CERTIFICATE-----
MIIEYzCCA0ugAwIBAgIJAOP9Uyx2LzzOMA0GCSqGSIb3DQEBCwUAMH0xCzAJBgNV
BAYTAkRFMQ8wDQYDVQQIEwZCYXllcm4xFTATBgNVBAcTDEd1bnplbmhhdXNlbjEP
MA0GA1UEChMGSGlkZU1FMRIwEAYDVQQDEwlIaWRlTUUgQ0ExITAfBgkqhkiG9w0B
CQEWEmZlZWRiYWNrQGhpZGVtZS5ydTAgFw0yMDA5MDMxODQ2MDVaGA8yMDcwMDgy
MjE4NDYwNVowfTELMAkGA1UEBhMCREUxDzANBgNVBAgTBkJheWVybjEVMBMGA1UE
BxMMR3VuemVuaGF1c2VuMQ8wDQYDVQQKEwZIaWRlTUUxEjAQBgNVBAMTCUhpZGVN
RSBDQTEhMB8GCSqGSIb3DQEJARYSZmVlZGJhY2tAaGlkZW1lLnJ1MIIBIjANBgkq
hkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA5RcPoJweDQny9QtDQp3P7MtMJIqrkkQH
O0uj/+DoeGGgLo98FIxv6HMIhkGoGsvGS+6FAbH1Ul+wxFRVPb3WXQ0uF4JcThJu
QsyWJShcbJrcOnOUCryDfHXvYjvdruf6vxFA3FrRdmDrTqw6ITaD3gveax6p6hL4
wsHGBMytyC+QCCDJwyrx8apV5iIaNFNpJ4Ys06HgnGLcUrvtYWwXT5XUJV1qCCZG
gQ/ZAI8cJ4+KS+kzrPQPnpM5KyLuYl5vIf6WgJHN4BVbncnATKs77peJ4/P6JMEQ
f+jWWcQXoOYXn2drPu/d0wLO53Xn6sB+T7U5iHNGF8761tSTCU1yXwIDAQABo4Hj
MIHgMB0GA1UdDgQWBBRzwg1vUkbkU2AsEvr6YkLSRFDNqzCBsAYDVR0jBIGoMIGl
gBRzwg1vUkbkU2AsEvr6YkLSRFDNq6GBgaR/MH0xCzAJBgNVBAYTAkRFMQ8wDQYD
VQQIEwZCYXllcm4xFTATBgNVBAcTDEd1bnplbmhhdXNlbjEPMA0GA1UEChMGSGlk
ZU1FMRIwEAYDVQQDEwlIaWRlTUUgQ0ExITAfBgkqhkiG9w0BCQEWEmZlZWRiYWNr
QGhpZGVtZS5ydYIJAOP9Uyx2LzzOMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQEL
BQADggEBAF0x8coIuVdGohOK4bWCLAfi5gRzN8wcw7bF0mOzpn4AEg8I7RFyXmp/
PUQDLYReqaTY95crM6YtepcrvQ8neHViqW9dgCh1e25Xacz3sePMMnyuIZaUyUna
5Vrn20yXp3F+4nxVnWmVPEwRlLNGgNsxrun03zoMfbj73VOH/hhnb0SyId33oMc8
3GSEiOtiwicjUqcVypD8fnKHJWNMloqUsCLOsP2RmoXRDXRO4hYMx3E27HYDkKd8
GsPH0L/8w5rEIQ8MDV7p0ly8TgApKc4x7JqeS8KzYnqeWDW0Do4QpzLbqDwbZEvl
ANKoMP3Q+ewcpb/Rza7dnVBZKCAgWu8=
-----END CERTIFICATE-----
</ca>

<cert>
-----BEGIN CERTIFICATE-----
MIIEwTCCA6mgAwIBAgIEAKrgQzANBgkqhkiG9w0BAQsFADB9MQswCQYDVQQGEwJE
RTEPMA0GA1UECBMGQmF5ZXJuMRUwEwYDVQQHEwxHdW56ZW5oYXVzZW4xDzANBgNV
BAoTBkhpZGVNRTESMBAGA1UEAxMJSGlkZU1FIENBMSEwHwYJKoZIhvcNAQkBFhJm
ZWVkYmFja0BoaWRlbWUucnUwHhcNMjUwOTA5MTQzOTI0WhcNMjYwOTE0MTQzOTI0
WjCBkTELMAkGA1UEBhMCREUxDzANBgNVBAgTBkJheWVybjEVMBMGA1UEBxMMR3Vu
emVuaGF1c2VuMRQwEgYDVQQKEwtoaWRlbXkubmFtZTEfMB0GA1UEAxQWaGlkZW1l
XzYzMjAwNjU0NDg5OTE5NTEjMCEGCSqGSIb3DQEJARYUZmVlZGJhY2tAaGlkZW15
Lm5hbWUwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDj1sozGMoXxPFc
GC3TNeNJCyVx3FyXD/cZhqg6ILx3n1yNa6N0QTlJgU/U9/xtP/9KxnDndwEO20t
Gmiey2CsXe9KULo2of9gnHyAMFqODhIm5oZdLx+azVEdTDrVqgfG1U0N/tUpiObM
LGYJOqiVNRy9XIvwSnNwsht98f9PJLsX1/L1JDWubFaau4EnSe+Sw9j1WDqrh7OL
cVTd9QTZmHyjKCuQL2kSg0fbKLpIMJQvslqoSt/bpwV9Efk2pNtWWqFbDhufckmV
RhnosMoOZIVZncLk+djbvbqiWe3SAt4ze46sdaAsZiAvEYrHQA8TB1NHPYq3Ucqb
v56BP2eBAgMBAAGjggEyMIIBLjAJBgNVHRMEAjAAMC0GCWCGSAGG+EIBDQQgFh5F
YXN5LVJTQSBHZW5lcmF0ZWQgQ2VydGlmaWNhdGUwHQYDVR0OBBYEFH+XDHNz/unn
FZI63FFvI7tyHGtwMIGwBgNVHSMEgagwgaWAFHPCDW9SRuRTYCwS+vpiQtJEUM2r
oYGBpH8wfTELMAkGA1UEBhMCREUxDzANBgNVBAgTBkJheWVybjEVMBMGA1UEBxMM
R3VuemVuaGF1c2VuMQ8wDQYDVQQKEwZIaWRlTUUxEjAQBgNVBAMTCUhpZGVNRSBD
QTEhMB8GCSqGSIb3DQEJARYSZmVlZGJhY2tAaGlkZW1lLnJ1ggkA4/1TLHYvPM4w
EwYDVR0lBAwwCgYIKwYBBQUHAwIwCwYDVR0PBAQDAgeAMA0GCSqGSIb3DQEBCwUA
A4IBAQChW3uzkE10TmGXlEox4BOwr7/QOACMrr+l/Usiqh19eIkC/3YseCqJXrPf
D89YLYs59DFNN3N/y8EO1WfGH2muQ7xjy7fN3bFlEj+biKXdRf8cff9kJBY/d33J
i4Y7E9uGCzZEMk+zQ7fYISlrQuoBvzrTRkrY1d62NA0ugmU0rkj2bVwt7J2cXTaE
ozg8N3Hy9Dv/+tGwfnVzkMcagXYxHbZUranYd1P1p2oo74sjKBR45efmHxYJ6MoU
hVUK4CcbxzjQtUjX+5il6f3+wPRC9+p5ADCBA7EWHwGSp3TVB6A2wtJNPnZp2yrB
ThlJ5d0sWBXhfsDsnquNd9wzfHoC
-----END CERTIFICATE-----
</cert>

<key>
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDj1sozGMoXxPFc
GC3TNeNJCyVXx3FyXD/cZhqg6ILx3n1yNa6N0QTlJgU/U9/xtP/9KxnDndwEO20t
Gmiey2CsXe9KULo2of9gnHyAMFqODhIm5oZdLx+azVEdTDrVqgfG1U0N/tUpiObM
LGYJOqiVNRy9XIvwSnNwsht98f9PJLsX1/L1JDWubFaau4EnSe+Sw9j1WDqrh7OL
cVTd9QTZmHyjKCuQL2kSg0fbKLpIMJQvslqoSt/bpwV9Efk2pNtWWqFbDhufckmV
RhnosMoOZIVZncLk+djbvbqiWe3SAt4ze46sdaAsZiAvEYrHQA8TB1NHPYq3Ucqb
v56BP2eBAgMBAAECggEAHw0tII/5LF/NyeXiX53sBzlK0m70TLLljIr+h73jPsXl
EJWKtSREB7D0rR/9bj/jVY80Dd+BVrL8sFV1kGgabv4cYzijsFdyv9QupE/dakKL
rHE65bn1k4+g8EkX3vqIiyDomrGHlAdm9nOknQ8Os8skdWsGssM1ftSfVOe639UD
++e6E6PW9yJ9J4lE3+WiEZr5AWDJ6KFV9WHRsTEIWqzHFGQCcM4ZdeWMWjclL+Rq
rkp9jPYt/YEVO3En8a1LMpuxvwwHNr2pS3+nsacnLe1Wo1SyEXvtEjz5kpTwNpJb
fS82vt5fMxe8VVC7Y9dCTek2mAeFqHekanINXaFagwKBgQD74iyCwQrhBh60siCv
oFM0QKLr3g5hEstDwCifvoseV1YKc9a1gRuxdhivzqMIiJ6+lPIgJgvDMRfyD2i+
CK3WSBgTNQarWj5S7r5dBKSbSQ67VN3Xm8fQrbYOxk+gk/Xk7SWMmtREVyTyVWtA
nIn0x/7n/bBSnvny6zGCvNgVswKBgQDnkATkNchm32CwWTkOedidPQ05Enqvj+HY
1RQLauC4YvAzAo+IVMajhi8wyI5ny7Rw646iYmH0yvQxF6L9siA/iGY/cR1JFkrb
tXgWga+D5edV1Y2+xPhs6513eCs4eNfPQ+r1kymoG23vquQlHDRPQTYGM2DtSe7s
8wDFAObb+wKBgQDQWnedNRfNqaVOrSXygPkyeOELoKReUhCHm3U/JnunfnDytn19
qC2DLwAetRwRHAnL9iMOysniDUMUfQCUaVN6tCoOAUfiCAUTzt7yzLtopBcmiH31
MqwnhvnY4NvPJXU6h5wO4agCW995AYV1bceEDsdhmWz3+v8gnMJYteM8lwKBgQCc
BFEHYaVQipieuL7UngvwhT3vgh/fQdYtPgNvXedi1GZ6N/N1K4lajAInoDkyffFp
U4yapCbTxBqbKQ3MWMOZitE5VYEhyT9OoQn0QBR9jd0729LRAe1PlcBWykR0nBbr
sxsPssOSXEjJ/h4RUtt7urgnnV5lAjdUtrWCBoWFGQKBgFWG3kJJ4XTdhm8FTLdz
4+nenRBhNyRwTJ0n/6lJbN84jqr2245LVZgUS888nIbmCjjJ+4FMC9I34JmMwdO0
lFuf1h8oSARYJzhPh5yejkxRQMKrS5AqQ3EawHyl5ysHgeRQpFh48JnudMAi7Ja0
V+4iuQUDvZm8DkLc6pNndUBG
-----END PRIVATE KEY-----
</key>

<tls-crypt>
#
# 2048 bit OpenVPN static key
#
-----BEGIN OpenVPN Static key V1-----
a07b0ba4befcb5cc99c0637f3c7ba378
b3391c2709f8b4d3fadc94de2fada0c8
a533e346edfeb88a86cad82a45050d2d
d23e86adc40695c793fc8e7bca13e09e
ef65003847e2427b8b3094ec0bb42050
eae1eed918d8be7fedae9ce2242cf117
ba8a99407256a0287aae69e7e2227894
3729ccb89760c6568039a3844db5e283
e9bd99d183191db578fa679b6f52ef9f
c2aabebb8438f20fc6b9ceeaf5446936
ff587e5f2b2498b1641fe9a9524823b2
01f48b2400b1ead5b75c3717629c1c7d
7255491479c6ab987180e9cb28461237
e1010cbb438cc94964f9985621259e50
4c6b3aeb552f20c81a7445c8b0b4ee1e
b28d157ab34b6236dd1bb334f352fa46
-----END OpenVPN Static key V1-----
</tls-crypt>
VPNEOF
"

echo ""
echo "✅ Конфигурация создана!"
echo ""
echo "⚠️  ВАЖНО: Перед запуском VPN убедитесь, что:"
echo "   1. VPN остановлен: systemctl stop openvpn-client"
echo "   2. Вы можете подключиться по SSH"
echo ""
echo "▶️  Запуск VPN..."
remote_exec "systemctl start openvpn-client"
sleep 5

echo ""
echo "🔍 Проверка статуса..."
remote_exec "systemctl status openvpn-client --no-pager | head -10"

echo ""
echo "✅ Настройка завершена!"
echo ""
echo "📋 Что было сделано:"
echo "   ✓ Policy-based routing настроен"
echo "   ✓ SSH трафик (порт 22) исключен из VPN"
echo "   ✓ Остальной трафик идет через VPN"
echo ""
echo "🔍 Проверка:"
echo "   - SSH: ssh root@95.81.96.59 (должен работать)"
echo "   - Внешний IP: curl ifconfig.me (должен быть IP VPN)"
echo "   - Логи: tail -f /var/log/openvpn-client.log"

