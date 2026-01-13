#!/usr/bin/env python3
"""
Маршруты для редактирования глоссария
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from pathlib import Path
import json
from app.config import Config
from app.models.activity_log import ActivityLog, db

bp = Blueprint('glossary', __name__, url_prefix='/glossary')


@bp.route('/')
@login_required
def index():
    """Страница редактора глоссария"""
    if not current_user.is_admin:
        return "Доступ запрещен", 403
    return render_template('glossary/index.html')


@bp.route('/api/get', methods=['GET'])
@login_required
def get_glossary():
    """Получить глоссарий"""
    if not current_user.is_admin:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    try:
        glossary_file = Config.GLOSSARY_FILE
        if not glossary_file.exists():
            return jsonify({'error': 'Файл глоссария не найден'}), 404
        
        with open(glossary_file, 'r', encoding='utf-8') as f:
            glossary = json.load(f)
        
        return jsonify({
            'success': True,
            'glossary': glossary
        })
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Ошибка парсинга JSON: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Ошибка чтения файла: {str(e)}'}), 500


@bp.route('/api/save', methods=['POST'])
@login_required
def save_glossary():
    """Сохранить глоссарий"""
    if not current_user.is_admin:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    try:
        data = request.get_json()
        if not data or 'glossary' not in data:
            return jsonify({'error': 'Неверный формат данных'}), 400
        
        glossary = data['glossary']
        
        # Валидация JSON
        json.dumps(glossary)  # Проверка на валидность
        
        # Создаем резервную копию
        glossary_file = Config.GLOSSARY_FILE
        if glossary_file.exists():
            backup_file = glossary_file.with_suffix('.json.backup')
            with open(glossary_file, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(backup_content)
        
        # Сохраняем новый глоссарий
        glossary_file.parent.mkdir(parents=True, exist_ok=True)
        with open(glossary_file, 'w', encoding='utf-8') as f:
            json.dump(glossary, f, ensure_ascii=False, indent=2)
        
        # Логируем действие
        ActivityLog.log_activity(
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            action='glossary_updated',
            details='Глоссарий обновлен'
        )
        
        return jsonify({
            'success': True,
            'message': 'Глоссарий успешно сохранен'
        })
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Неверный формат JSON: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Ошибка сохранения: {str(e)}'}), 500


@bp.route('/api/validate', methods=['POST'])
@login_required
def validate_glossary():
    """Валидация структуры глоссария"""
    if not current_user.is_admin:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    try:
        data = request.get_json()
        if not data or 'glossary' not in data:
            return jsonify({'error': 'Неверный формат данных'}), 400
        
        glossary = data['glossary']
        errors = []
        
        def validate_structure(obj, path=""):
            """Рекурсивная валидация структуры"""
            if not isinstance(obj, dict):
                errors.append(f"{path}: должен быть объектом")
                return
            
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, dict):
                    # Проверяем, есть ли обязательные поля
                    if 'match' in value or 'unit' in value:
                        # Это конечный узел
                        if 'match' in value and value['match'] is not None:
                            if not isinstance(value['match'], list):
                                errors.append(f"{current_path}.match: должен быть массивом")
                        if 'unit' not in value:
                            errors.append(f"{current_path}: отсутствует поле 'unit'")
                    else:
                        # Это промежуточный узел, продолжаем рекурсию
                        validate_structure(value, current_path)
                else:
                    errors.append(f"{current_path}: неверный тип данных")
        
        validate_structure(glossary)
        
        return jsonify({
            'success': len(errors) == 0,
            'errors': errors
        })
    except Exception as e:
        return jsonify({'error': f'Ошибка валидации: {str(e)}'}), 500

