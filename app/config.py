#!/usr/bin/env python3
"""
Конфигурация приложения
Поддерживает разные окружения (development, production, testing)
"""

import os
from pathlib import Path


class Config:
    """Базовая конфигурация"""
    
    # Безопасность
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Ограничения файлов
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}
    
    # Пути к директориям
    BASE_DIR = Path(__file__).parent.parent
    UPLOAD_FOLDER = BASE_DIR / 'storage' / 'uploads'
    OUTPUT_FOLDER = BASE_DIR / 'storage' / 'converted'
    RESULTS_FOLDER = BASE_DIR / 'storage' / 'results'
    DEBUG_FOLDER = BASE_DIR / 'storage' / 'debug'
    LOG_FOLDER = BASE_DIR / 'logs'
    DATA_FOLDER = BASE_DIR / 'data'
    
    # Файлы шаблонов
    PROMPT_TEMPLATE_FILE = DATA_FOLDER / 'Промпт.txt'
    TZ_TEMPLATE_FILE = DATA_FOLDER / 'TZ.json'
    GLOSSARY_FILE = DATA_FOLDER / 'glossary.json'
    
    # API ключи
    API_KEY_FILE = BASE_DIR / 'key.txt'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-5')
    
    # AI провайдеры
    DEFAULT_AI_PROVIDER = 'openai'
    SUPPORTED_AI_PROVIDERS = ['openai', 'jayflow']
    
    # Настройки Flask
    JSON_AS_ASCII = False
    JSONIFY_PRETTYPRINT_REGULAR = True


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    TESTING = False
    
    # Переопределяем SECRET_KEY для продакшена
    # В продакшене SECRET_KEY должен быть установлен через переменную окружения
    SECRET_KEY = os.environ.get('SECRET_KEY') or Config.SECRET_KEY


class TestingConfig(Config):
    """Конфигурация для тестирования"""
    DEBUG = True
    TESTING = True
    
    # Используем временные директории для тестов
    UPLOAD_FOLDER = Path('/tmp/ai_manager_test/uploads')
    OUTPUT_FOLDER = Path('/tmp/ai_manager_test/converted')
    RESULTS_FOLDER = Path('/tmp/ai_manager_test/results')


# Словарь конфигураций
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

