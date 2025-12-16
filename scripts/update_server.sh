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
remote_exec "cd $PROJECT_DIR && source venv/bin/activate && pip install -q --upgrade pip && pip install -q -r requirements.txt"

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
echo "🗄️  Шаг 7: Инициализация базы данных..."
remote_exec "cd $PROJECT_DIR && source venv/bin/activate && python3 -c 'from app import create_app; app = create_app(); app.app_context().push(); from app.models.db import db; db.create_all(); print(\"✅ База данных инициализирована\")' || echo '⚠️  База данных уже существует или ошибка инициализации'"

echo ""
echo "✅ Обновление завершено!"
echo ""
echo "📝 Что было обновлено:"
echo "   ✓ Система пользователей (регистрация, авторизация)"
echo "   ✓ История обработок документов"
echo "   ✓ Логи активности (для админов)"
echo "   ✓ Привязка документов к пользователям"
echo "   ✓ Проверка прав доступа"
echo ""
echo "🔍 Проверка:"
echo "   - Логи: sudo journalctl -u ai-manager -f"
echo "   - Статус: sudo systemctl status ai-manager"
echo "   - База данных: $PROJECT_DIR/storage/app.db"
echo ""
echo "👤 Администратор по умолчанию:"
echo "   Логин: admin"
echo "   Пароль: admin"
echo "   ⚠️  Смените пароль после первого входа!"

