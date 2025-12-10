#!/bin/bash
# Тест подключения к OpenAI через прокси напрямую

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"
PROXY="http://210.79.146.234:8080"

echo "🧪 Тест подключения к OpenAI через прокси"
echo "=========================================="
echo ""

# Функция для выполнения команд на удаленном сервере
remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

echo "1️⃣ Тест через curl..."
HTTP_CODE=$(remote_exec "curl -x $PROXY --max-time 15 -s -o /dev/null -w '%{http_code}' https://api.openai.com/v1/models")
echo "   HTTP код: $HTTP_CODE"

echo ""
echo "2️⃣ Тест через Python с httpx..."
remote_exec "cd /home/aimanager/ai-manager && source venv/bin/activate && python3 << 'PYEOF'
import httpx
import os

proxy = '$PROXY'
os.environ['HTTP_PROXY'] = proxy
os.environ['HTTPS_PROXY'] = proxy

try:
    client = httpx.Client(proxies={'http://': proxy, 'https://': proxy}, timeout=15.0)
    response = client.get('https://api.openai.com/v1/models')
    print(f'   Статус: {response.status_code}')
    if response.status_code < 500:
        print('   ✅ Подключение работает')
    else:
        print(f'   ⚠️  Ошибка: {response.status_code}')
except Exception as e:
    print(f'   ❌ Ошибка: {e}')
PYEOF
"

echo ""
echo "3️⃣ Проверка таймаутов..."
echo "   Если тесты показывают ошибки таймаута, попробуйте:"
echo "   - Увеличить timeout в коде"
echo "   - Использовать другой прокси"
echo "   - Проверить доступность прокси"

