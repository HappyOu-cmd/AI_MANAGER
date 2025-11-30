#!/bin/bash
# Скрипт для загрузки AI Manager на GitHub

echo "🚀 Загрузка AI Manager на GitHub"
echo "=================================="
echo ""

# Проверка наличия remote
if git remote | grep -q origin; then
    echo "✅ Remote 'origin' уже настроен"
    git remote -v
else
    echo "📝 Настройка remote репозитория"
    echo ""
    echo "Введите URL вашего GitHub репозитория:"
    echo "Пример: https://github.com/username/ai-manager.git"
    echo "   или: git@github.com:username/ai-manager.git"
    read -p "URL: " repo_url
    
    if [ -z "$repo_url" ]; then
        echo "❌ URL не указан. Выход."
        exit 1
    fi
    
    git remote add origin "$repo_url"
    echo "✅ Remote добавлен: $repo_url"
fi

echo ""
echo "📤 Отправка кода на GitHub..."
echo ""

# Проверка текущей ветки
current_branch=$(git branch --show-current)
echo "Текущая ветка: $current_branch"

# Push на GitHub
if git push -u origin "$current_branch"; then
    echo ""
    echo "✅ Код успешно загружен на GitHub!"
    echo ""
    echo "🌐 Ваш репозиторий доступен по адресу:"
    git remote get-url origin | sed 's/\.git$//' | sed 's/git@github.com:/https:\/\/github.com\//'
else
    echo ""
    echo "❌ Ошибка при загрузке. Возможные причины:"
    echo "   1. Репозиторий не создан на GitHub"
    echo "   2. Неверный URL"
    echo "   3. Проблемы с аутентификацией"
    echo ""
    echo "💡 Решения:"
    echo "   1. Создайте репозиторий на GitHub: https://github.com/new"
    echo "   2. Используйте Personal Access Token для HTTPS"
    echo "   3. Настройте SSH ключи для git@github.com"
fi

