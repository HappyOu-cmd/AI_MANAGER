#!/bin/bash
# Проверка подключения к OpenAI БЕЗ прокси

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"

echo "🔍 Проверка подключения к OpenAI БЕЗ прокси"
echo "============================================"
echo ""

remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

echo "1️⃣ Проверка DNS..."
remote_exec "nslookup platform.openai.com 2>&1 | head -5"

echo ""
echo "2️⃣ Проверка через curl (platform.openai.com)..."
remote_exec "curl --max-time 10 -I https://platform.openai.com 2>&1 | head -5"

echo ""
echo "3️⃣ Проверка через curl (api.openai.com)..."
remote_exec "curl --max-time 10 -I https://api.openai.com 2>&1 | head -5"

echo ""
echo "4️⃣ Проверка через Python без прокси..."
remote_exec "cd /home/aimanager/ai-manager && source venv/bin/activate && python3 << 'PYEOF'
import httpx
import os

# Удаляем все переменные прокси
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'OPENAI_PROXY']:
    os.environ.pop(key, None)

print('Тест platform.openai.com:')
try:
    response = httpx.get('https://platform.openai.com', timeout=10.0)
    print(f'  Статус: {response.status_code}')
    if response.status_code == 200:
        print('  ✅ Доступен!')
except Exception as e:
    print(f'  ❌ Ошибка: {type(e).__name__}')

print('')
print('Тест api.openai.com:')
try:
    response = httpx.get('https://api.openai.com/v1/models', timeout=10.0)
    print(f'  Статус: {response.status_code}')
    if response.status_code in [200, 401]:
        print('  ✅ Доступен!')
except Exception as e:
    print(f'  ❌ Ошибка: {type(e).__name__}: {str(e)[:80]}')
PYEOF
"

echo ""
echo "✅ Проверка завершена!"

