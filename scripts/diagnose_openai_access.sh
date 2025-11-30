#!/bin/bash
# Диагностика доступности OpenAI и геолокации сервера

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"

echo "🔍 Диагностика доступности OpenAI"
echo "=================================="
echo ""

# Функция для выполнения команд на удаленном сервере
remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

echo "🛑 Шаг 1: Остановка VPN..."
remote_exec "systemctl stop openvpn-client || true"
sleep 2

echo ""
echo "🌍 Шаг 2: Проверка геолокации сервера..."
echo "   IP сервера: 95.81.96.59"
echo "   Проверка геолокации..."

# Проверяем геолокацию через несколько сервисов
GEO_INFO=$(remote_exec "curl -s --max-time 5 'https://ipapi.co/95.81.96.59/json/' 2>&1")
echo "$GEO_INFO" | grep -E '"country_name"|"city"|"region"|"org"' || echo "   Не удалось получить геолокацию"

echo ""
echo "📡 Шаг 3: Проверка доступности OpenAI API..."
echo "   Тестирую подключение к api.openai.com..."

# Проверка DNS
echo "   DNS резолюция:"
DNS_RESULT=$(remote_exec "nslookup api.openai.com 2>&1 | grep -A 2 'Name:' | head -3")
echo "$DNS_RESULT"

# Проверка HTTP подключения
echo ""
echo "   HTTP подключение:"
HTTP_RESULT=$(remote_exec "curl -s --max-time 10 -I https://api.openai.com 2>&1 | head -5")
echo "$HTTP_RESULT"

# Проверка конкретного эндпоинта
echo ""
echo "   Тест эндпоинта /v1/models:"
MODELS_RESULT=$(remote_exec "curl -s --max-time 10 https://api.openai.com/v1/models 2>&1 | head -3")
echo "$MODELS_RESULT"

# Проверка через разные DNS серверы
echo ""
echo "📊 Шаг 4: Проверка через разные DNS..."
echo "   Google DNS (8.8.8.8):"
GOOGLE_DNS=$(remote_exec "dig @8.8.8.8 api.openai.com +short 2>&1 | head -3")
echo "   $GOOGLE_DNS"

echo "   Cloudflare DNS (1.1.1.1):"
CF_DNS=$(remote_exec "dig @1.1.1.1 api.openai.com +short 2>&1 | head -3")
echo "   $CF_DNS"

# Проверка маршрутизации
echo ""
echo "🛣️  Шаг 5: Проверка маршрутизации к OpenAI..."
TRACEROUTE=$(remote_exec "traceroute -m 10 -w 2 api.openai.com 2>&1 | head -10")
echo "$TRACEROUTE"

# Проверка блокировок
echo ""
echo "🚫 Шаг 6: Проверка на блокировки..."
echo "   Проверка через curl с разными User-Agent:"
UA_RESULT=$(remote_exec "curl -s --max-time 10 -H 'User-Agent: Mozilla/5.0' https://api.openai.com 2>&1 | head -3")
echo "$UA_RESULT"

# Проверка внешнего IP
echo ""
echo "🌐 Шаг 7: Текущий внешний IP сервера:"
EXTERNAL_IP=$(remote_exec "curl -s --max-time 5 ifconfig.me 2>&1")
echo "   $EXTERNAL_IP"

# Проверка через прокси (если доступен)
echo ""
echo "📋 Шаг 8: Сводка результатов..."
echo "   IP сервера: 95.81.96.59"
echo "   Внешний IP: $EXTERNAL_IP"
echo "   VPN статус: остановлен"

echo ""
echo "✅ Диагностика завершена!"
echo ""
echo "📝 Следующие шаги:"
echo "   1. Проанализируйте результаты выше"
echo "   2. Если OpenAI недоступен - нужен VPN из другой страны"
echo "   3. Если доступен - проблема может быть в другом"

