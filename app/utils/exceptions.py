#!/usr/bin/env python3
"""
Кастомные исключения для приложения
"""


class AIManagerException(Exception):
    """Базовое исключение для AI Manager"""
    pass


class ValidationError(AIManagerException):
    """Ошибка валидации данных"""
    pass


class DocumentConversionError(AIManagerException):
    """Ошибка конвертации документа"""
    pass


class AIProcessingError(AIManagerException):
    """Ошибка обработки ИИ"""
    pass


class ConfigurationError(AIManagerException):
    """Ошибка конфигурации"""
    pass


class FileNotFoundError(AIManagerException):
    """Файл не найден"""
    pass

