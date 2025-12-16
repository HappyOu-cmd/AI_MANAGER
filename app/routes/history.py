#!/usr/bin/env python3
"""
Маршруты для истории обработок пользователя
"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.models.db import db
from app.models.document import Document
from datetime import datetime, timedelta

bp = Blueprint('history', __name__, url_prefix='/history')


@bp.route('/')
@login_required
def index():
    """Страница истории обработок"""
    # Получаем параметры фильтрации
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status_filter = request.args.get('status', 'all')
    
    # Запрос документов пользователя
    query = Document.query.filter_by(user_id=current_user.id)
    
    # Фильтр по статусу
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # Сортировка по дате создания (новые сначала)
    query = query.order_by(Document.created_at.desc())
    
    # Пагинация
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    documents = pagination.items
    
    return render_template(
        'history/index.html',
        documents=documents,
        pagination=pagination,
        status_filter=status_filter
    )


@bp.route('/api/documents')
@login_required
def api_documents():
    """API: Получить список документов пользователя"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Document.query.filter_by(user_id=current_user.id)
    query = query.order_by(Document.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    documents = []
    for doc in pagination.items:
        documents.append({
            'id': doc.id,
            'task_id': doc.task_id,
            'original_filename': doc.original_filename,
            'scenario_id': doc.scenario_id,
            'ai_provider': doc.ai_provider,
            'status': doc.status,
            'json_file': doc.json_file,
            'excel_file': doc.excel_file,
            'json_size': doc.json_size,
            'excel_size': doc.excel_size,
            'tokens_used': doc.tokens_used,
            'processing_time': doc.processing_time,
            'created_at': doc.created_at.isoformat() if doc.created_at else None,
            'completed_at': doc.completed_at.isoformat() if doc.completed_at else None,
            'json_url': f'/download_result/{doc.json_file}' if doc.json_file else None,
            'excel_url': f'/download_result/{doc.excel_file}' if doc.excel_file else None
        })
    
    return jsonify({
        'documents': documents,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })
