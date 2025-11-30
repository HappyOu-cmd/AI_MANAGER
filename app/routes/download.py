#!/usr/bin/env python3
"""
Маршруты для скачивания файлов
"""

from flask import Blueprint, send_file, jsonify, current_app
from werkzeug.utils import secure_filename
from pathlib import Path

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
def download_result(filename):
    """Скачивание заполненного JSON или Excel файла"""
    file_path = Path(current_app.config['RESULTS_FOLDER']) / secure_filename(filename)
    
    if not file_path.exists():
        return jsonify({'error': 'Файл не найден'}), 404
    
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

