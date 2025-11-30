#!/usr/bin/env python3
"""
Маршруты для загрузки и обработки файлов
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from pathlib import Path

from app.services.document_service import DocumentService
from app.services.ai_service import AIService
from app.utils.validators import FileValidator
from app.utils.exceptions import ValidationError, DocumentConversionError, AIProcessingError

bp = Blueprint('upload', __name__)


@bp.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки, конвертации и заполнения ТЗ через ИИ"""
    try:
        # Валидация запроса
        if 'file' not in request.files:
            raise ValidationError('Файл не выбран')
        
        file = request.files['file']
        
        if file.filename == '':
            raise ValidationError('Файл не выбран')
        
        # Валидация файла
        validator = FileValidator(
            allowed_extensions=current_app.config['ALLOWED_EXTENSIONS'],
            max_size=current_app.config['MAX_CONTENT_LENGTH']
        )
        
        is_valid, error_msg = validator.validate_file(
            file.filename,
            file.content_length
        )
        
        if not is_valid:
            raise ValidationError(error_msg)
        
        # Сохраняем файл
        filename = validator.secure_filename(file.filename)
        upload_path = Path(current_app.config['UPLOAD_FOLDER']) / filename
        file.save(str(upload_path))
        
        current_app.logger.info(f"Файл загружен: {filename}")
        
        # Обрабатываем документ
        document_service = DocumentService(current_app.config)
        result = document_service.process_document(
            str(upload_path),
            request.form.get('ai_provider', current_app.config['DEFAULT_AI_PROVIDER'])
        )
        
        return jsonify(result)
    
    except ValidationError as e:
        current_app.logger.warning(f"Ошибка валидации: {e}")
        return jsonify({'error': str(e)}), 400
    
    except DocumentConversionError as e:
        current_app.logger.error(f"Ошибка конвертации: {e}")
        return jsonify({
            'error': str(e),
            'stage': 'conversion'
        }), 500
    
    except AIProcessingError as e:
        current_app.logger.error(f"Ошибка обработки ИИ: {e}")
        return jsonify({
            'error': str(e),
            'stage': 'ai_processing'
        }), 500
    
    except Exception as e:
        current_app.logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
        return jsonify({
            'error': f'Ошибка обработки: {str(e)}',
            'stage': 'unknown'
        }), 500

