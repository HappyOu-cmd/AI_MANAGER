#!/bin/bash
# Скрипт для обновления AI Manager на сервере из GitHub

SSH_HOST="root@95.81.96.59"
SSH_PASS="Userbe362f!"
PROJECT_DIR="/home/aimanager/ai-manager"

echo "🔄 Обновление AI Manager на сервере"
echo "===================================="
echo ""

# Функция для выполнения команд на удаленном сервере
remote_exec() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_HOST" "$@"
}

echo "📦 Шаг 1: Остановка сервиса..."
remote_exec "systemctl stop ai-manager || true"
sleep 2

echo ""
echo "📥 Шаг 2: Обновление кода из GitHub..."
remote_exec "cd $PROJECT_DIR && git config --global --add safe.directory $PROJECT_DIR || true"
remote_exec "cd $PROJECT_DIR && git fetch origin"
remote_exec "cd $PROJECT_DIR && git stash || true"
remote_exec "cd $PROJECT_DIR && git reset --hard origin/main"
remote_exec "cd $PROJECT_DIR && git pull origin main"

echo ""
echo "📋 Шаг 3: Установка новых зависимостей..."
remote_exec "cd $PROJECT_DIR && source venv/bin/activate && pip install -q httpx || pip install httpx"

echo ""
echo "✅ Шаг 4: Проверка изменений..."
remote_exec "cd $PROJECT_DIR && git log --oneline -5"

echo ""
echo "▶️  Шаг 5: Запуск сервиса..."
remote_exec "systemctl start ai-manager"
sleep 3

echo ""
echo "🔍 Шаг 6: Проверка статуса..."
remote_exec "systemctl status ai-manager --no-pager | head -15"

echo ""
echo "✅ Обновление завершено!"
echo ""
echo "📝 Что было обновлено:"
echo "   ✓ Поддержка прокси для OpenAI"
echo "   ✓ Новые скрипты для VPN и прокси"
echo "   ✓ Обновленные зависимости (httpx)"
echo ""
echo "🔍 Проверка:"
echo "   - Логи: sudo journalctl -u ai-manager -f"
echo "   - Статус: sudo systemctl status ai-manager"

