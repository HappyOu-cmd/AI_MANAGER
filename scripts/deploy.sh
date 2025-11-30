#!/bin/bash
# Скрипт для обновления AI Manager на сервере через GitHub

# Не используем set -e, чтобы обрабатывать ошибки вручную

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"
APP_USER="aimanager"
APP_DIR="/home/${APP_USER}/ai-manager"
REPO_URL="https://github.com/HappyOu-cmd/AI_MANAGER.git"
SERVICE_NAME="ai-manager"

echo "🔄 Обновление AI Manager на сервере через GitHub"
echo "================================================"
echo ""

# Функция для выполнения команд на удаленном сервере
remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

echo "📥 Шаг 1: Получение последних изменений из GitHub..."
# Получаем последние изменения
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && git fetch origin'"

# Проверяем, есть ли локальные изменения
HAS_CHANGES=$(remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && git status --porcelain'" | wc -l)

if [ "$HAS_CHANGES" -gt 0 ]; then
    echo "   ⚠️  Обнаружены локальные изменения на сервере"
    echo "   Сохраняем их в stash и обновляем с GitHub..."
    remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && git stash save \"Local changes before deploy $(date)\"'"
fi

# Обновляем с GitHub
PULL_RESULT=$(remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && git pull origin main'" 2>&1)

if [ $? -ne 0 ]; then
    echo "   ⚠️  Конфликт при обновлении. Принудительно обновляем с GitHub..."
    remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && git reset --hard origin/main'"
    
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка при получении изменений из GitHub"
        echo "   Проверьте, что репозиторий настроен правильно"
        exit 1
    fi
    echo "   ✅ Принудительное обновление завершено"
else
    echo "   ✅ Обновление с GitHub успешно"
fi

echo ""
echo "🐍 Шаг 2: Обновление Python зависимостей..."
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && source venv/bin/activate && pip install -r requirements.txt'"

echo ""
echo "📁 Шаг 3: Проверка структуры директорий..."
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && mkdir -p data storage/{uploads,converted,results,debug} logs'"

echo ""
echo "🔑 Шаг 4: Проверка API ключа..."
if remote_exec "test -f ${APP_DIR}/key.txt"; then
    echo "   ✅ API ключ на месте"
else
    echo "   ⚠️  API ключ отсутствует! Нужно добавить вручную."
    echo "   Выполните на сервере:"
    echo "   echo 'your-api-key' > ${APP_DIR}/key.txt"
fi

echo ""
echo "📋 Шаг 5: Проверка файлов данных..."
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && ls -la data/Промпт.txt data/TZ.json data/glossary.json 2>/dev/null || echo \"⚠️  Некоторые файлы данных отсутствуют\"'"

echo ""
echo "🔄 Шаг 6: Перезапуск сервиса..."
remote_exec "systemctl restart ${SERVICE_NAME}"
sleep 3

echo ""
echo "✅ Обновление завершено!"
echo ""
echo "🔍 Проверка работы:"
HEALTH_CHECK=$(remote_exec "curl -s http://localhost:5000/health" || echo "ERROR")
if echo "$HEALTH_CHECK" | grep -q "ok"; then
    echo "   ✅ Сервис работает корректно"
else
    echo "   ⚠️  Проблема с сервисом. Проверьте логи:"
    echo "   journalctl -u ${SERVICE_NAME} -f"
fi

echo ""
echo "📝 Статус сервиса:"
remote_exec "systemctl status ${SERVICE_NAME} --no-pager | head -15"

echo ""
echo "🌐 Приложение доступно по адресу: http://95.81.96.59"

