#!/bin/bash
# Скрипт для полной переустановки AI Manager на сервере

set -e

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"
APP_USER="aimanager"
APP_DIR="/home/${APP_USER}/ai-manager"
REPO_URL="https://github.com/HappyOu-cmd/AI_MANAGER.git"
SERVICE_NAME="ai-manager"

echo "🔄 Полная переустановка AI Manager на сервере"
echo "=============================================="
echo ""

# Функция для выполнения команд на удаленном сервере
remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

echo "🛑 Шаг 1: Остановка сервиса..."
remote_exec "systemctl stop ${SERVICE_NAME} || true"

echo ""
echo "🗑️  Шаг 2: Удаление старой версии..."
remote_exec "su - ${APP_USER} -c 'rm -rf ${APP_DIR}'"

echo ""
echo "📥 Шаг 3: Клонирование репозитория..."
remote_exec "su - ${APP_USER} -c 'cd /home/${APP_USER} && git clone ${REPO_URL} ai-manager'"

echo ""
echo "🔑 Шаг 4: Восстановление API ключа..."
# Сохраняем ключ перед удалением (если был)
OLD_KEY=$(remote_exec "cat ${APP_DIR}/key.txt 2>/dev/null" || echo "")
if [ -z "$OLD_KEY" ]; then
    echo "   ⚠️  API ключ не найден в старой версии"
    echo "   Нужно будет добавить вручную после установки"
else
    echo "   ✅ API ключ найден, будет восстановлен"
    remote_exec "su - ${APP_USER} -c 'echo \"${OLD_KEY}\" > ${APP_DIR}/key.txt && chmod 600 ${APP_DIR}/key.txt'"
fi

echo ""
echo "🐍 Шаг 5: Создание виртуального окружения и установка зависимостей..."
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && python3 -m venv venv && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && pip install gunicorn'"

echo ""
echo "📁 Шаг 6: Создание необходимых директорий..."
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && mkdir -p storage/{uploads,converted,results,debug} logs'"

echo ""
echo "🔍 Шаг 7: Проверка файлов данных..."
remote_exec "su - ${APP_USER} -c 'cd ${APP_DIR} && ls -la data/Промпт.txt data/TZ.json data/glossary.json'"

echo ""
echo "⚙️  Шаг 8: Создание systemd сервиса..."
# Создаем systemd unit файл напрямую на сервере
remote_exec "cat > /tmp/ai-manager.service << 'SERVICEEOF'
[Unit]
Description=AI Manager Flask Application
After=network.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=\"PATH=${APP_DIR}/venv/bin\"
ExecStart=${APP_DIR}/venv/bin/gunicorn \\
    --workers 3 \\
    --bind 127.0.0.1:5000 \\
    --timeout 300 \\
    run:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF
mv /tmp/ai-manager.service /etc/systemd/system/${SERVICE_NAME}.service
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}"

echo ""
echo "🌐 Шаг 9: Настройка Nginx..."
# Создаем конфигурацию Nginx напрямую на сервере
remote_exec "cat > /tmp/ai-manager-nginx << 'NGINXEOF'
server {
    listen 80;
    server_name 95.81.96.59;

    client_max_body_size 50M;

    # Статические файлы - обрабатываем через Flask
    location /static {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }

    # Основное приложение
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
NGINXEOF
mv /tmp/ai-manager-nginx /etc/nginx/sites-available/${SERVICE_NAME}
ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx"

echo ""
echo "▶️  Шаг 10: Запуск сервиса..."
remote_exec "systemctl start ${SERVICE_NAME}"
sleep 3

echo ""
echo "✅ Переустановка завершена!"
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
echo ""
echo "⚠️  Важно:"
if [ -z "$OLD_KEY" ]; then
    echo "   - API ключ не был восстановлен. Добавьте его:"
    echo "     echo 'your-api-key' > ${APP_DIR}/key.txt"
fi
echo "   - Проверьте права доступа к файлам:"
echo "     chown -R ${APP_USER}:${APP_USER} ${APP_DIR}"

