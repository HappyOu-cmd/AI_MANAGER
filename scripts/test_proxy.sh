#!/bin/bash
# Скрипт для тестирования прокси перед настройкой

if [ -z "$1" ]; then
    echo "Использование: $0 <proxy-url>"
    echo "Пример: $0 http://proxy.example.com:8080"
    echo "Пример с авторизацией: $0 http://user:pass@proxy.example.com:8080"
    exit 1
fi

PROXY_URL="$1"

echo "🔍 Тестирование прокси: $PROXY_URL"
echo "=================================="
echo ""

# Тест 1: Базовая доступность
echo "📡 Тест 1: Проверка доступности прокси..."
if curl -x "$PROXY_URL" --max-time 10 -s -o /dev/null -w "%{http_code}" https://www.google.com > /dev/null 2>&1; then
    echo "   ✅ Прокси доступен"
else
    echo "   ❌ Прокси недоступен или не работает"
    exit 1
fi

# Тест 2: Подключение к OpenAI через прокси
echo ""
echo "🤖 Тест 2: Подключение к OpenAI API через прокси..."
HTTP_CODE=$(curl -x "$PROXY_URL" --max-time 10 -s -o /dev/null -w "%{http_code}" https://api.openai.com)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "421" ]; then
    echo "   ✅ Подключение к OpenAI работает (HTTP $HTTP_CODE)"
else
    echo "   ⚠️  Неожиданный код ответа: $HTTP_CODE"
fi

# Тест 3: Проверка внешнего IP через прокси
echo ""
echo "🌐 Тест 3: Проверка внешнего IP через прокси..."
EXTERNAL_IP=$(curl -x "$PROXY_URL" --max-time 10 -s ifconfig.me 2>/dev/null)
if [ -n "$EXTERNAL_IP" ]; then
    echo "   ✅ Внешний IP через прокси: $EXTERNAL_IP"
    
    # Проверка геолокации
    echo "   📍 Проверка геолокации..."
    GEO=$(curl -s --max-time 5 "https://ipapi.co/$EXTERNAL_IP/json/" 2>&1 | grep -E '"country_name"|"city"' | head -2)
    echo "   $GEO"
else
    echo "   ⚠️  Не удалось определить внешний IP"
fi

# Тест 4: Скорость подключения
echo ""
echo "⚡ Тест 4: Скорость подключения..."
START_TIME=$(date +%s%N)
curl -x "$PROXY_URL" --max-time 10 -s -o /dev/null https://api.openai.com > /dev/null 2>&1
END_TIME=$(date +%s%N)
DURATION=$(( (END_TIME - START_TIME) / 1000000 ))
echo "   ⏱️  Время ответа: ${DURATION}ms"

if [ "$DURATION" -lt 2000 ]; then
    echo "   ✅ Скорость хорошая"
elif [ "$DURATION" -lt 5000 ]; then
    echo "   ⚠️  Скорость средняя"
else
    echo "   ❌ Скорость низкая"
fi

echo ""
echo "✅ Тестирование завершено!"
echo ""
echo "📝 Если все тесты пройдены, используйте этот прокси:"
echo "   export OPENAI_PROXY=\"$PROXY_URL\""

