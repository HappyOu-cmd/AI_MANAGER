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
    safe_filename = secure_filename(filename)
    file_path = Path(current_app.config['RESULTS_FOLDER']) / safe_filename
    
    if not file_path.exists():
        return jsonify({'error': 'Файл не найден'}), 404
    
    # Проверяем права доступа - находим документ по имени файла
    doc = Document.query.filter(
        (Document.json_file == safe_filename) | (Document.excel_file == safe_filename)
    ).first()
    
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

