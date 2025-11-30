#!/usr/bin/env python3
"""
Точка входа для запуска AI Manager
"""

import os
from app import create_app
from app.config import config

# Определяем окружение
env = os.environ.get('FLASK_ENV', 'development')

# Создаем приложение
app = create_app(config.get(env, config['default']))

if __name__ == '__main__':
    print("=" * 60)
    print("🌐 AI Manager - Веб-интерфейс для заполнения ТЗ через ИИ")
    print("=" * 60)
    print(f"📂 Окружение: {env}")
    print(f"📂 Загрузки: {app.config['UPLOAD_FOLDER']}")
    print(f"📄 Конвертированные: {app.config['OUTPUT_FOLDER']}")
    print(f"✅ Результаты: {app.config['RESULTS_FOLDER']}")
    print(f"🌍 Откройте в браузере: http://127.0.0.1:5000")
    print()
    
    # Проверка API ключа
    api_key = app.config.get('OPENAI_API_KEY')
    api_key_file = app.config.get('API_KEY_FILE')
    
    if api_key_file and api_key_file.exists():
        try:
            with open(api_key_file, 'r', encoding='utf-8') as f:
                api_key = f.read().strip()
            if api_key:
                print(f"✅ OpenAI API ключ найден в key.txt (первые 10 символов: {api_key[:10]}...)")
        except Exception as e:
            print(f"⚠️  Ошибка чтения key.txt: {e}")
    
    if not api_key:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            print(f"✅ OpenAI API ключ найден в переменной окружения (первые 10 символов: {api_key[:10]}...)")
        else:
            print("⚠️  API ключ не найден!")
            print("   Создайте файл key.txt в корне проекта или установите:")
            print("   export OPENAI_API_KEY='your-key-here'")
    
    print("=" * 60)
    print()
    
    # Запускаем приложение
    app.run(
        debug=app.config.get('DEBUG', False),
        host='0.0.0.0',
        port=5000
    )

