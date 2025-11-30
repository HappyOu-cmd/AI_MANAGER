#!/bin/bash
# Скрипт для настройки прокси из списка на сервере

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"

if [ -z "$1" ]; then
    echo "Использование: $0 <proxy-url>"
    echo ""
    echo "Примеры из вашего списка:"
    echo "  США (рекомендуется для OpenAI):"
    echo "    $0 http://205.164.46.6:3128"
    echo ""
    echo "  HTTPS прокси:"
    echo "    $0 http://49.48.94.235:8080"
    echo "    $0 http://210.79.146.234:8080"
    echo ""
    echo "  SOCKS5 (требует httpx[socks]):"
    echo "    $0 socks5://103.54.217.82:8199"
    exit 1
fi

PROXY_URL="$1"

echo "🔧 Настройка прокси для OpenAI на сервере"
echo "=========================================="
echo ""
echo "Прокси: $PROXY_URL"
echo ""

# Функция для выполнения команд на удаленном сервере
remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

echo "📡 Шаг 1: Тестирование прокси..."
# Тестируем прокси локально
if curl -x "$PROXY_URL" --max-time 10 -s -o /dev/null -w "%{http_code}" https://api.openai.com > /dev/null 2>&1; then
    echo "   ✅ Прокси доступен и работает"
else
    echo "   ⚠️  Прокси может быть недоступен, но продолжим настройку"
fi

echo ""
echo "🌐 Шаг 2: Проверка внешнего IP через прокси..."
EXTERNAL_IP=$(curl -x "$PROXY_URL" --max-time 10 -s ifconfig.me 2>/dev/null)
if [ -n "$EXTERNAL_IP" ]; then
    echo "   Внешний IP через прокси: $EXTERNAL_IP"
    
    # Проверка геолокации
    GEO=$(curl -s --max-time 5 "https://ipapi.co/$EXTERNAL_IP/json/" 2>&1 | grep -E '"country_name"|"city"' | head -2)
    echo "   Геолокация: $GEO"
else
    echo "   ⚠️  Не удалось определить внешний IP"
fi

echo ""
echo "⚙️  Шаг 3: Настройка на сервере..."
echo "   Проверяю текущий systemd service..."

# Проверяем, существует ли сервис
SERVICE_FILE="/etc/systemd/system/ai-manager.service"
if remote_exec "test -f $SERVICE_FILE"; then
    echo "   ✅ Сервис найден"
    
    # Делаем backup
    remote_exec "cp $SERVICE_FILE ${SERVICE_FILE}.backup.$(date +%s)"
    
    # Добавляем или обновляем переменную окружения
    if remote_exec "grep -q 'OPENAI_PROXY' $SERVICE_FILE"; then
        echo "   Обновляю существующую настройку прокси..."
        remote_exec "sed -i 's|Environment=\"OPENAI_PROXY=.*\"|Environment=\"OPENAI_PROXY=$PROXY_URL\"|' $SERVICE_FILE"
    else
        echo "   Добавляю настройку прокси..."
        # Находим секцию [Service] и добавляем после неё
        remote_exec "sed -i '/\[Service\]/a Environment=\"OPENAI_PROXY=$PROXY_URL\"' $SERVICE_FILE"
    fi
    
    echo ""
    echo "   Перезагружаю systemd и перезапускаю сервис..."
    remote_exec "systemctl daemon-reload"
    remote_exec "systemctl restart ai-manager"
    
    echo ""
    echo "   Проверка статуса сервиса..."
    sleep 2
    remote_exec "systemctl status ai-manager --no-pager | head -10"
    
else
    echo "   ⚠️  Сервис не найден. Создайте его вручную или используйте переменную окружения."
    echo ""
    echo "   Альтернативный способ - через переменную окружения:"
    echo "   export OPENAI_PROXY=\"$PROXY_URL\""
fi

echo ""
echo "✅ Настройка завершена!"
echo ""
echo "🔍 Проверка:"
echo "   1. Проверьте логи: sudo journalctl -u ai-manager -f"
echo "   2. Попробуйте загрузить файл через веб-интерфейс"
echo "   3. Проверьте, что запросы к OpenAI идут через прокси"
echo ""
echo "📝 Если нужно отключить прокси:"
echo "   Удалите строку Environment=\"OPENAI_PROXY=...\" из $SERVICE_FILE"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl restart ai-manager"

