#!/bin/bash
# Тест подключения к OpenAI с текущими настройками

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"

echo "🧪 Тест подключения к OpenAI"
echo "============================="
echo ""

remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

echo "1️⃣ Проверка переменных окружения..."
PROXY=$(remote_exec "systemctl show ai-manager --property=Environment --no-pager | grep -oP 'OPENAI_PROXY=\K[^ ]+'")
echo "   Прокси: $PROXY"

echo ""
echo "2️⃣ Тест через curl с прокси..."
remote_exec "curl -x $PROXY --max-time 15 -s -I https://api.openai.com 2>&1 | head -3"

echo ""
echo "3️⃣ Тест через Python с переменными окружения..."
remote_exec "cd /home/aimanager/ai-manager && source venv/bin/activate && python3 << 'PYEOF'
import os
import httpx

proxy = '$PROXY'
os.environ['HTTP_PROXY'] = proxy
os.environ['HTTPS_PROXY'] = proxy

print('Тестирую с переменными окружения...')
try:
    # httpx автоматически подхватит переменные окружения
    response = httpx.get('https://api.openai.com/v1/models', timeout=15.0)
    print(f'Статус: {response.status_code}')
    if response.status_code < 500:
        print('✅ Подключение работает')
    else:
        print(f'⚠️  Ошибка: {response.status_code}')
except Exception as e:
    print(f'❌ Ошибка: {type(e).__name__}: {e}')
PYEOF
"

echo ""
echo "4️⃣ Проверка логов сервиса..."
remote_exec "journalctl -u ai-manager --no-pager -n 10 | grep -iE 'error|connection' | tail -3"

