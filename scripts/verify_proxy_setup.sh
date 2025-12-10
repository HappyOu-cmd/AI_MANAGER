#!/bin/bash
# Скрипт для проверки настроенного прокси на сервере

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"

echo "🔍 Проверка настроенного прокси на сервере"
echo "==========================================="
echo ""

# Функция для выполнения команд на удаленном сервере
remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

echo "1️⃣ Проверка переменной окружения в systemd..."
PROXY_CONFIG=$(remote_exec "systemctl show ai-manager --property=Environment --no-pager | grep OPENAI_PROXY")
echo "   $PROXY_CONFIG"

if echo "$PROXY_CONFIG" | grep -q "OPENAI_PROXY"; then
    PROXY_URL=$(echo "$PROXY_CONFIG" | grep -oP 'OPENAI_PROXY=\K[^ ]+')
    echo "   ✅ Прокси настроен: $PROXY_URL"
else
    echo "   ❌ Прокси не настроен"
    exit 1
fi

echo ""
echo "2️⃣ Проверка доступности прокси..."
if remote_exec "curl -x $PROXY_URL --max-time 5 -s -o /dev/null -w '%{http_code}' https://api.openai.com" | grep -qE '[0-9]{3}'; then
    echo "   ✅ Прокси доступен и работает"
else
    echo "   ⚠️  Прокси может быть недоступен"
fi

echo ""
echo "3️⃣ Проверка внешнего IP через прокси..."
EXTERNAL_IP=$(remote_exec "curl -x $PROXY_URL --max-time 5 -s ifconfig.me 2>&1")
echo "   Внешний IP через прокси: $EXTERNAL_IP"

echo ""
echo "4️⃣ Проверка в Python коде..."
PYTHON_CHECK=$(remote_exec "cd /home/aimanager/ai-manager && source venv/bin/activate && python3 -c \"
import os
from app.core.ai.openai_client import OpenAIClient

proxy_env = os.environ.get('OPENAI_PROXY', 'Не установлен')
print(f'Переменная окружения: {proxy_env}')

client = OpenAIClient()
print(f'Прокси в клиенте: {client.proxy if client.proxy else \"Не установлен\"}')
\"")
echo "$PYTHON_CHECK" | sed 's/^/   /'

echo ""
echo "5️⃣ Статус сервиса..."
remote_exec "systemctl is-active ai-manager && echo '   ✅ Сервис активен' || echo '   ❌ Сервис неактивен'"

echo ""
echo "✅ Проверка завершена!"
echo ""
echo "📝 Следующие шаги:"
echo "   1. Протестируйте загрузку файла через веб-интерфейс"
echo "   2. Проверьте логи: sudo journalctl -u ai-manager -f"
echo "   3. Убедитесь, что запросы к OpenAI проходят через прокси"

