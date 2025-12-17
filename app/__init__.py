#!/usr/bin/env python3
"""
AI Manager - Flask Application Factory
Масштабируемое веб-приложение для автоматического заполнения ТЗ с помощью ИИ
"""

from flask import Flask, request
from flask_login import LoginManager
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

from app.config import Config, ProductionConfig
from app.models.db import db


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
    
    # Инициализируем базу данных
    db.init_app(app)
    with app.app_context():
        db.create_all()
        # Создаем админа по умолчанию если его нет
        _create_default_admin(app)
    
    # Настраиваем Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # Добавляем current_user в контекст шаблонов (на случай если Flask-Login не делает это автоматически)
    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return dict(current_user=current_user)
    
    # Настраиваем логирование
    _setup_logging(app)
    
    # Регистрируем blueprints
    from app.routes import main, upload, download, scenarios, auth, history, logs, admin
    app.register_blueprint(main.bp)
    app.register_blueprint(upload.bp)
    app.register_blueprint(download.bp)
    app.register_blueprint(scenarios.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(history.bp)
    app.register_blueprint(logs.bp)
    app.register_blueprint(admin.bp)
    
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
    # Всегда логируем в файл (и в debug, и в production)
    log_file = Path(app.config['LOG_FOLDER']) / 'app.log'
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    # Настраиваем логирование для модулей
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        handlers=[file_handler]
    )
    
    # Устанавливаем уровень логирования для наших модулей
    logging.getLogger('src.scenario_executor').setLevel(logging.INFO)
    logging.getLogger('src.ai_client').setLevel(logging.INFO)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('AI Manager startup')


def _create_default_admin(app):
    """Создает администратора по умолчанию если его нет"""
    from app.models.user import User
    
    try:
        # Проверяем существующего админа
        admin = User.query.filter_by(username='kosharov.ilya.r').first()
        if not admin:
            # Создаем нового админа
            admin = User(
                username='kosharov.ilya.r',
                email='kosharov.ilya.r@example.com',
                is_admin=True
            )
            admin.set_password('hjvf25')
            db.session.add(admin)
            db.session.commit()
            app.logger.info('✅ Создан администратор: kosharov.ilya.r')
        else:
            # Обновляем пароль существующего админа
            admin.set_password('hjvf25')
            admin.is_admin = True
            db.session.commit()
            app.logger.info('✅ Обновлен пароль администратора: kosharov.ilya.r')
        
        # Удаляем старого админа admin если он существует
        old_admin = User.query.filter_by(username='admin').first()
        if old_admin and old_admin.username != 'kosharov.ilya.r':
            db.session.delete(old_admin)
            db.session.commit()
            app.logger.info('✅ Удален старый администратор: admin')
    except Exception as e:
        db.session.rollback()
        app.logger.warning(f'⚠️  Ошибка при создании администратора: {e}')

