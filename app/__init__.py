#!/usr/bin/env python3
"""
AI Manager - Flask Application Factory
Масштабируемое веб-приложение для автоматического заполнения ТЗ с помощью ИИ
"""

from flask import Flask, request
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

from app.config import Config, ProductionConfig


def create_app(config_class=Config):
    """
    Factory функция для создания Flask приложения
    
    Args:
        config_class: Класс конфигурации
        
    Returns:
        Настроенное Flask приложение
    """
    # Определяем корневую директорию проекта (на уровень выше app/)
    base_dir = Path(__file__).parent.parent
    
    # Создаем Flask приложение с явными путями к templates и static
    app = Flask(
        __name__,
        template_folder=str(base_dir / 'templates'),
        static_folder=str(base_dir / 'static'),
        static_url_path='/static'
    )
    app.config.from_object(config_class)
    
    # Проверка SECRET_KEY для продакшена (только когда используется ProductionConfig)
    if config_class == ProductionConfig:
        if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'] == Config.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY должен быть установлен в переменной окружения для продакшена!\n"
                "Установите: export SECRET_KEY='your-secret-key-here'"
            )
    
    # Создаем необходимые директории
    _create_directories(app)
    
    # Настраиваем логирование
    _setup_logging(app)
    
    # Регистрируем blueprints
    from app.routes import main, upload, download
    app.register_blueprint(main.bp)
    app.register_blueprint(upload.bp)
    app.register_blueprint(download.bp)
    
    # Регистрируем обработчики ошибок
    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Убеждаемся, что все ошибки возвращаются как JSON для API запросов
    @app.after_request
    def after_request(response):
        # Если запрос к API и ответ не JSON, конвертируем ошибки в JSON
        if request.path.startswith('/upload') or request.path.startswith('/download'):
            if response.status_code >= 400 and not response.is_json:
                try:
                    # Пытаемся извлечь текст ошибки из HTML
                    from flask import jsonify
                    error_data = {
                        'error': f'Ошибка {response.status_code}',
                        'message': response.status
                    }
                    response = jsonify(error_data)
                    response.status_code = response.status_code
                except:
                    pass
        return response
    
    return app


def _create_directories(app):
    """Создает необходимые директории для работы приложения"""
    directories = [
        app.config['UPLOAD_FOLDER'],
        app.config['OUTPUT_FOLDER'],
        app.config['RESULTS_FOLDER'],
        app.config['DEBUG_FOLDER'],
        app.config['LOG_FOLDER'],
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def _setup_logging(app):
    """Настраивает систему логирования"""
    if not app.debug:
        # Логирование в файл для продакшена
        log_file = Path(app.config['LOG_FOLDER']) / 'app.log'
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('AI Manager startup')

