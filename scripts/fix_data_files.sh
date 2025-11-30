#!/bin/bash
# Скрипт для исправления расположения файлов данных на сервере

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"
APP_USER="aimanager"
APP_DIR="/home/${APP_USER}/ai-manager"

echo "🔧 Исправление расположения файлов данных на сервере"
echo "====================================================="
echo ""

# Функция для выполнения команд на удаленном сервере
remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

echo "📁 Шаг 1: Создание папки data/..."
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && mkdir -p data'"

echo ""
echo "📋 Шаг 2: Проверка текущего расположения файлов..."
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && ls -la Промпт.txt TZ.json glossary.json 2>/dev/null || echo \"Файлы не найдены в корне\"'"

echo ""
echo "🔄 Шаг 3: Перемещение файлов в data/..."
# Перемещаем файлы, если они есть в корне
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && 
    if [ -f Промпт.txt ] && [ ! -f data/Промпт.txt ]; then
        mv Промпт.txt data/Промпт.txt
        echo \"✅ Промпт.txt перемещен\"
    fi
    if [ -f TZ.json ] && [ ! -f data/TZ.json ]; then
        mv TZ.json data/TZ.json
        echo \"✅ TZ.json перемещен\"
    fi
    if [ -f glossary.json ] && [ ! -f data/glossary.json ]; then
        mv glossary.json data/glossary.json
        echo \"✅ glossary.json перемещен\"
    fi
'"

echo ""
echo "✅ Проверка результата..."
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && ls -la data/'"

echo ""
echo "🔄 Шаг 4: Обновление git репозитория..."
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && git reset --hard origin/main'"

echo ""
echo "✅ Исправление завершено!"
echo ""
echo "📋 Финальная проверка:"
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && echo \"Файлы в data/:\" && ls -la data/ && echo \"\" && echo \"Файлы в корне (не должно быть):\" && ls -la Промпт.txt TZ.json glossary.json 2>/dev/null || echo \"✅ Файлов в корне нет\"'"

