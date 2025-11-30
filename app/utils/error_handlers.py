#!/usr/bin/env python3
"""
Обработчики ошибок для Flask приложения
"""

from flask import jsonify, render_template
from app.utils.exceptions import AIProcessingError, DocumentConversionError, ValidationError


def register_error_handlers(app):
    """Регистрирует обработчики ошибок"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Неверный запрос', 'message': str(error)}), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Ресурс не найден', 'message': str(error)}), 404
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            'error': 'Файл слишком большой',
            'message': 'Превышен максимальный размер файла'
        }), 413
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}', exc_info=True)
        return jsonify({
            'error': 'Внутренняя ошибка сервера',
            'message': 'Произошла непредвиденная ошибка'
        }), 500
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify({
            'error': 'Ошибка валидации',
            'message': str(error)
        }), 400
    
    @app.errorhandler(DocumentConversionError)
    def handle_conversion_error(error):
        return jsonify({
            'error': 'Ошибка конвертации документа',
            'message': str(error),
            'stage': 'conversion'
        }), 500
    
    @app.errorhandler(AIProcessingError)
    def handle_ai_error(error):
        return jsonify({
            'error': 'Ошибка обработки ИИ',
            'message': str(error),
            'stage': 'ai_processing'
        }), 500

