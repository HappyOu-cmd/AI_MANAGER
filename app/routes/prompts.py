#!/usr/bin/env python3
"""
Маршруты для редактирования промптов
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from pathlib import Path
import json
from app.config import Config
from app.models.activity_log import ActivityLog, db

bp = Blueprint('prompts', __name__, url_prefix='/prompts')


@bp.route('/')
@login_required
def index():
    """Страница редактора промптов"""
    if not current_user.is_admin:
        return "Доступ запрещен", 403
    return render_template('prompts/index.html')


@bp.route('/api/list', methods=['GET'])
@login_required
def list_prompts():
    """Получить список всех промптов"""
    if not current_user.is_admin:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    try:
        prompts_dir = Config.DATA_FOLDER / 'prompts'
        prompts = []
        
        if prompts_dir.exists():
            for prompt_file in prompts_dir.rglob('*.txt'):
                relative_path = prompt_file.relative_to(prompts_dir)
                prompts.append({
                    'path': str(relative_path).replace('\\', '/'),
                    'name': prompt_file.name,
                    'category': relative_path.parent.name if relative_path.parent != Path('.') else 'root'
                })
        
        return jsonify({
            'success': True,
            'prompts': sorted(prompts, key=lambda x: x['path'])
        })
    except Exception as e:
        return jsonify({'error': f'Ошибка получения списка: {str(e)}'}), 500


@bp.route('/api/get', methods=['GET'])
@login_required
def get_prompt():
    """Получить содержимое промпта"""
    if not current_user.is_admin:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    try:
        path = request.args.get('path')
        if not path:
            return jsonify({'error': 'Не указан путь к файлу'}), 400
        
        # Безопасность: проверяем, что путь не выходит за пределы директории
        prompts_dir = Config.DATA_FOLDER / 'prompts'
        prompt_file = (prompts_dir / path).resolve()
        
        if not str(prompt_file).startswith(str(prompts_dir.resolve())):
            return jsonify({'error': 'Неверный путь к файлу'}), 400
        
        if not prompt_file.exists():
            return jsonify({'error': 'Файл не найден'}), 404
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'content': content,
            'path': path
        })
    except Exception as e:
        return jsonify({'error': f'Ошибка чтения файла: {str(e)}'}), 500


@bp.route('/api/save', methods=['POST'])
@login_required
def save_prompt():
    """Сохранить промпт"""
    if not current_user.is_admin:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    try:
        data = request.get_json()
        if not data or 'content' not in data or 'path' not in data:
            return jsonify({'error': 'Неверный формат данных'}), 400
        
        path = data['path']
        content = data['content']
        
        # Безопасность: проверяем, что путь не выходит за пределы директории
        prompts_dir = Config.DATA_FOLDER / 'prompts'
        prompt_file = (prompts_dir / path).resolve()
        
        if not str(prompt_file).startswith(str(prompts_dir.resolve())):
            return jsonify({'error': 'Неверный путь к файлу'}), 400
        
        # Создаем резервную копию
        if prompt_file.exists():
            backup_file = prompt_file.with_suffix('.txt.backup')
            with open(prompt_file, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(backup_content)
        
        # Создаем директорию, если её нет
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем файл
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Логируем действие
        ActivityLog.log_activity(
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            action='prompt_updated',
            details=f'Промпт обновлен: {path}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Промпт успешно сохранен'
        })
    except Exception as e:
        return jsonify({'error': f'Ошибка сохранения: {str(e)}'}), 500


@bp.route('/api/create', methods=['POST'])
@login_required
def create_prompt():
    """Создать новый промпт"""
    if not current_user.is_admin:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    try:
        data = request.get_json()
        if not data or 'path' not in data:
            return jsonify({'error': 'Не указан путь к файлу'}), 400
        
        path = data['path']
        content = data.get('content', '')
        
        # Безопасность: проверяем, что путь не выходит за пределы директории
        prompts_dir = Config.DATA_FOLDER / 'prompts'
        prompt_file = (prompts_dir / path).resolve()
        
        if not str(prompt_file).startswith(str(prompts_dir.resolve())):
            return jsonify({'error': 'Неверный путь к файлу'}), 400
        
        if prompt_file.exists():
            return jsonify({'error': 'Файл уже существует'}), 400
        
        # Создаем директорию, если её нет
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Создаем файл
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Логируем действие
        ActivityLog.log_activity(
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            action='prompt_created',
            details=f'Промпт создан: {path}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Промпт успешно создан'
        })
    except Exception as e:
        return jsonify({'error': f'Ошибка создания: {str(e)}'}), 500


@bp.route('/api/delete', methods=['POST'])
@login_required
def delete_prompt():
    """Удалить промпт"""
    if not current_user.is_admin:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    try:
        data = request.get_json()
        if not data or 'path' not in data:
            return jsonify({'error': 'Не указан путь к файлу'}), 400
        
        path = data['path']
        
        # Безопасность: проверяем, что путь не выходит за пределы директории
        prompts_dir = Config.DATA_FOLDER / 'prompts'
        prompt_file = (prompts_dir / path).resolve()
        
        if not str(prompt_file).startswith(str(prompts_dir.resolve())):
            return jsonify({'error': 'Неверный путь к файлу'}), 400
        
        if not prompt_file.exists():
            return jsonify({'error': 'Файл не найден'}), 404
        
        # Удаляем файл
        prompt_file.unlink()
        
        # Логируем действие
        ActivityLog.log_activity(
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            action='prompt_deleted',
            details=f'Промпт удален: {path}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Промпт успешно удален'
        })
    except Exception as e:
        return jsonify({'error': f'Ошибка удаления: {str(e)}'}), 500

