#!/bin/bash
# Скрипт для быстрой смены прокси для OpenAI

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"
SERVICE_FILE="/etc/systemd/system/ai-manager.service"

if [ -z "$1" ]; then
    echo "🔄 Быстрая смена прокси для OpenAI"
    echo "==================================="
    echo ""
    echo "Использование: $0 <proxy-url>"
    echo ""
    echo "Примеры:"
    echo "  $0 http://210.79.146.234:8080"
    echo "  $0 http://49.48.94.235:8080"
    echo "  $0 http://proxy-host:port"
    echo ""
    echo "Для отключения прокси:"
    echo "  $0 off"
    echo ""
    echo "Текущий прокси:"
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" \
        "grep OPENAI_PROXY $SERVICE_FILE 2>/dev/null | head -1 || echo '  Не настроен'"
    exit 1
fi

PROXY_URL="$1"

echo "🔄 Смена прокси для OpenAI"
echo "=========================="
echo ""

# Функция для выполнения команд на удаленном сервере
remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

# Отключение прокси
if [ "$PROXY_URL" = "off" ] || [ "$PROXY_URL" = "disable" ] || [ "$PROXY_URL" = "none" ]; then
    echo "❌ Отключение прокси..."
    
    # Удаляем строку с OPENAI_PROXY
    remote_exec "sed -i '/OPENAI_PROXY/d' $SERVICE_FILE"
    
    echo "   ✅ Прокси отключен"
    echo ""
    echo "   Перезапуск сервиса..."
    remote_exec "systemctl daemon-reload"
    remote_exec "systemctl restart ai-manager"
    sleep 2
    
    echo ""
    echo "✅ Прокси отключен!"
    echo ""
    echo "📝 Проверка:"
    remote_exec "grep OPENAI_PROXY $SERVICE_FILE 2>/dev/null || echo '   Прокси не найден в конфигурации (отключен)'"
    exit 0
fi

# Проверка формата прокси
if [[ ! "$PROXY_URL" =~ ^https?:// ]] && [[ ! "$PROXY_URL" =~ ^socks5:// ]]; then
    echo "⚠️  Предупреждение: Прокси должен начинаться с http://, https:// или socks5://"
    echo "   Добавляю http:// автоматически..."
    PROXY_URL="http://$PROXY_URL"
fi

echo "📡 Тестирование прокси: $PROXY_URL"
echo ""

# Быстрая проверка доступности
if curl -x "$PROXY_URL" --max-time 5 -s -o /dev/null -w "%{http_code}" https://api.openai.com > /dev/null 2>&1; then
    echo "   ✅ Прокси доступен"
else
    echo "   ⚠️  Прокси может быть недоступен, но продолжим настройку"
fi

echo ""
echo "⚙️  Обновление конфигурации..."

# Делаем backup
remote_exec "cp $SERVICE_FILE ${SERVICE_FILE}.backup.\$(date +%s)"

# Обновляем или добавляем переменную окружения
if remote_exec "grep -q 'OPENAI_PROXY' $SERVICE_FILE"; then
    # Обновляем существующую строку
    remote_exec "sed -i 's|Environment=\"OPENAI_PROXY=.*\"|Environment=\"OPENAI_PROXY='$PROXY_URL'\"|' $SERVICE_FILE"
    echo "   ✅ Прокси обновлен"
else
    # Добавляем новую строку после [Service]
    remote_exec "sed -i '/\[Service\]/a Environment=\"OPENAI_PROXY='$PROXY_URL'\"' $SERVICE_FILE"
    echo "   ✅ Прокси добавлен"
fi

echo ""
echo "🔄 Перезапуск сервиса..."
remote_exec "systemctl daemon-reload"
remote_exec "systemctl restart ai-manager"
sleep 3

echo ""
echo "🔍 Проверка статуса..."
STATUS=$(remote_exec "systemctl is-active ai-manager")
if [ "$STATUS" = "active" ]; then
    echo "   ✅ Сервис активен"
else
    echo "   ⚠️  Сервис не активен, проверьте логи: sudo journalctl -u ai-manager -n 20"
fi

echo ""
echo "✅ Прокси изменен!"
echo ""
echo "📋 Текущая конфигурация:"
remote_exec "grep OPENAI_PROXY $SERVICE_FILE"
echo ""
echo "🌐 Проверка внешнего IP через прокси:"
EXTERNAL_IP=$(curl -x "$PROXY_URL" --max-time 5 -s ifconfig.me 2>/dev/null || echo "Не удалось определить")
echo "   $EXTERNAL_IP"
echo ""
echo "📝 Следующие шаги:"
echo "   1. Проверьте логи: sudo journalctl -u ai-manager -f"
echo "   2. Протестируйте загрузку файла через веб-интерфейс"
echo "   3. Убедитесь, что запросы к OpenAI работают"

