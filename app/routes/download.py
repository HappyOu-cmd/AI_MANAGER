#!/usr/bin/env python3
"""
Маршруты для скачивания файлов
"""

from flask import Blueprint, send_file, jsonify, current_app, abort, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from pathlib import Path
from app.models.db import db
from app.models.document import Document
from app.models.activity_log import ActivityLog

bp = Blueprint('download', __name__)


@bp.route('/download/<filename>')
def download_file(filename):
    """Скачивание сконвертированного текстового файла"""
    file_path = Path(current_app.config['OUTPUT_FOLDER']) / secure_filename(filename)
    
    if not file_path.exists():
        return jsonify({'error': 'Файл не найден'}), 404
    
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=filename,
        mimetype='text/plain'
    )


@bp.route('/download_result/<filename>')
@login_required
def download_result(filename):
    """Скачивание заполненного JSON или Excel файла (только для владельца)"""
    # Проверяем права доступа - находим документ по имени файла (используем оригинальное имя)
    doc = Document.query.filter(
        (Document.json_file == filename) | (Document.excel_file == filename)
    ).first()
    
    if not doc:
        # Если не найдено по оригинальному имени, пробуем secure_filename
        safe_filename = secure_filename(filename)
        doc = Document.query.filter(
            (Document.json_file == safe_filename) | (Document.excel_file == safe_filename)
        ).first()
    
    if not doc:
        # Если документ не найден в БД, проверяем, может это старый файл
        # Для безопасности запрещаем доступ, если нет записи в БД
        current_app.logger.warning(f"⚠️ Попытка скачать файл без записи в БД: {filename} пользователем {current_user.username}")
        abort(403)
    
    # Проверяем, что файл принадлежит текущему пользователю
    if doc.user_id != current_user.id:
        current_app.logger.warning(f"⚠️ Попытка несанкционированного доступа: пользователь {current_user.username} пытается скачать файл пользователя {doc.user_id}")
        abort(403)
    
    # Определяем имя файла для поиска на диске
    # Используем имя из БД
    if filename == doc.json_file or (doc.json_file and filename in doc.json_file):
        file_to_download = doc.json_file
    elif filename == doc.excel_file or (doc.excel_file and filename in doc.excel_file):
        file_to_download = doc.excel_file
    else:
        file_to_download = filename
    
    # Пробуем найти файл по имени из БД
    file_path = Path(current_app.config['RESULTS_FOLDER']) / file_to_download
    
    # Если не найден, пробуем разные варианты имени
    if not file_path.exists():
        # Вариант 1: secure_filename
        safe_filename = secure_filename(file_to_download)
        file_path = Path(current_app.config['RESULTS_FOLDER']) / safe_filename
        
        # Вариант 2: Поиск по task_id (если имя содержит task_id)
        if not file_path.exists() and doc.task_id:
            import os
            results_dir = Path(current_app.config['RESULTS_FOLDER'])
            # Ищем все файлы, начинающиеся с task_id
            for file in results_dir.glob(f"{doc.task_id}*"):
                if file.name.endswith('.json') and doc.json_file and '.json' in doc.json_file:
                    file_path = file
                    break
                elif file.name.endswith('.xlsx') and doc.excel_file and '.xlsx' in doc.excel_file:
                    file_path = file
                    break
    
    if not file_path.exists():
        current_app.logger.error(f"❌ Файл не найден на диске: {file_to_download} (проверено: {file_path})")
        current_app.logger.error(f"   Task ID: {doc.task_id}, JSON: {doc.json_file}, Excel: {doc.excel_file}")
        # Показываем список файлов в директории для отладки
        results_dir = Path(current_app.config['RESULTS_FOLDER'])
        if results_dir.exists():
            files = list(results_dir.glob(f"{doc.task_id}*"))
            current_app.logger.error(f"   Найдено файлов с task_id: {[f.name for f in files]}")
        return jsonify({'error': 'Файл не найден'}), 404
    
    if not doc:
        # Если документ не найден в БД, проверяем, может это старый файл
        # Для безопасности запрещаем доступ, если нет записи в БД
        current_app.logger.warning(f"⚠️ Попытка скачать файл без записи в БД: {safe_filename} пользователем {current_user.username}")
        abort(403)
    
    # Проверяем, что файл принадлежит текущему пользователю
    if doc.user_id != current_user.id:
        current_app.logger.warning(f"⚠️ Попытка несанкционированного доступа: пользователь {current_user.username} пытается скачать файл пользователя {doc.user_id}")
        abort(403)
    
    # Логируем скачивание
    try:
        log_entry = ActivityLog(
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            action='download',
            details=f'Скачивание файла: {safe_filename}',
            task_id=doc.task_id
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.warning(f"⚠️  Ошибка логирования скачивания: {e}")
    
    # Определяем MIME тип по расширению
    if filename.endswith('.xlsx'):
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif filename.endswith('.json'):
        mimetype = 'application/json'
    else:
        mimetype = 'application/octet-stream'
    
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )

