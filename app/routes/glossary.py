#!/usr/bin/env python3
"""
Маршруты для редактирования глоссария
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from pathlib import Path
import json
from app.config import Config
from app.models.db import db


def normalize_glossary(obj):
    """Нормализует глоссарий: пустые массивы и пустые строки -> null"""
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if isinstance(value, dict):
                # Проверяем, является ли это конечным узлом (есть match или unit)
                if 'match' in value or 'unit' in value:
                    normalized_value = {}
                    # Нормализуем match
                    if 'match' in value:
                        if isinstance(value['match'], list):
                            # Убираем пустые строки
                            match_filtered = [m for m in value['match'] if m and str(m).strip()]
                            normalized_value['match'] = match_filtered if match_filtered else None
                        elif isinstance(value['match'], str):
                            normalized_value['match'] = value['match'].strip() if value['match'].strip() else None
                        else:
                            normalized_value['match'] = value['match']
                    else:
                        normalized_value['match'] = None
                    
                    # Нормализуем unit
                    if 'unit' in value:
                        if isinstance(value['unit'], list):
                            # Убираем пустые строки
                            unit_filtered = [u for u in value['unit'] if u and str(u).strip()]
                            normalized_value['unit'] = unit_filtered if unit_filtered else None
                        elif isinstance(value['unit'], str):
                            normalized_value['unit'] = value['unit'].strip() if value['unit'].strip() else None
                        else:
                            normalized_value['unit'] = value['unit']
                    else:
                        normalized_value['unit'] = None
                    
                    result[key] = normalized_value
                else:
                    # Промежуточный узел, продолжаем рекурсию
                    result[key] = normalize_glossary(value)
            else:
                result[key] = value
        return result
    return obj

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
        
        # Нормализация данных: пустые массивы и пустые строки -> null
        glossary = normalize_glossary(glossary)
        
        # Валидация JSON
        json.dumps(glossary)  # Проверка на валидность
        
        # Создаем резервную копию
        glossary_file = Config.GLOSSARY_FILE
        if glossary_file.exists():
            backup_file = glossary_file.with_suffix('.json.backup')
            try:
                with open(glossary_file, 'r', encoding='utf-8') as f:
                    backup_content = f.read()
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
            except Exception as e:
                # Если не удалось создать резервную копию, продолжаем
                pass
        
        # Сохраняем новый глоссарий
        glossary_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Пытаемся исправить права доступа перед сохранением
            if glossary_file.exists():
                import os
                try:
                    # Получаем текущего пользователя процесса
                    import pwd
                    current_uid = os.getuid()
                    current_user_info = pwd.getpwuid(current_uid)
                    os.chown(glossary_file, current_uid, current_user_info.pw_gid)
                    os.chmod(glossary_file, 0o664)
                except (OSError, KeyError, AttributeError):
                    # Если не удалось изменить права, продолжаем попытку записи
                    pass
            
            with open(glossary_file, 'w', encoding='utf-8') as f:
                json.dump(glossary, f, ensure_ascii=False, indent=2)
            
            # Устанавливаем правильные права после записи
            try:
                import os
                import pwd
                current_uid = os.getuid()
                current_user_info = pwd.getpwuid(current_uid)
                os.chown(glossary_file, current_uid, current_user_info.pw_gid)
                os.chmod(glossary_file, 0o664)
            except (OSError, KeyError, AttributeError):
                pass
                
        except PermissionError as e:
            return jsonify({
                'error': f'Ошибка доступа к файлу: {str(e)}. Обратитесь к администратору сервера для исправления прав доступа.'
            }), 500
        
        # Логируем действие
        try:
            from app.routes.upload import log_activity
            log_activity(
                user_id=current_user.id,
                username=current_user.username,
                ip_address=request.remote_addr,
                action='glossary_updated',
                details='Глоссарий обновлен'
            )
        except Exception as e:
            # Не прерываем сохранение глоссария из-за ошибки логирования
            pass
        
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

