#!/usr/bin/env python3
"""
Маршруты для просмотра логов активности (только для админов)
"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.models.db import db
from app.models.activity_log import ActivityLog
from app.models.user import User
from datetime import datetime, timedelta

bp = Blueprint('logs', __name__, url_prefix='/logs')


def admin_required(f):
    """Декоратор для проверки прав администратора"""
    from functools import wraps
    
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            from flask import abort
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/')
@admin_required
def index():
    """Страница логов активности"""
    # Получаем параметры фильтрации
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    action_filter = request.args.get('action', 'all')
    username_filter = request.args.get('username', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Запрос логов
    query = ActivityLog.query
    
    # Фильтры
    if action_filter != 'all':
        query = query.filter_by(action=action_filter)
    
    if username_filter:
        query = query.filter(ActivityLog.username.like(f'%{username_filter}%'))
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(ActivityLog.created_at >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(ActivityLog.created_at < date_to_obj)
        except ValueError:
            pass
    
    # Сортировка по дате (новые сначала)
    query = query.order_by(ActivityLog.created_at.desc())
    
    # Пагинация
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    
    # Статистика
    total_logs = ActivityLog.query.count()
    unique_users = db.session.query(ActivityLog.user_id).distinct().count()
    
    # Топ действий
    from sqlalchemy import func
    top_actions = db.session.query(
        ActivityLog.action,
        func.count(ActivityLog.id).label('count')
    ).group_by(ActivityLog.action).order_by(func.count(ActivityLog.id).desc()).limit(10).all()
    
    return render_template(
        'logs/index.html',
        logs=logs,
        pagination=pagination,
        action_filter=action_filter,
        username_filter=username_filter,
        date_from=date_from,
        date_to=date_to,
        total_logs=total_logs,
        unique_users=unique_users,
        top_actions=top_actions
    )


@bp.route('/api/activity')
@admin_required
def api_activity():
    """API: Получить логи активности"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    action_filter = request.args.get('action', 'all')
    
    query = ActivityLog.query
    
    if action_filter != 'all':
        query = query.filter_by(action=action_filter)
    
    query = query.order_by(ActivityLog.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    logs = []
    for log in pagination.items:
        logs.append({
            'id': log.id,
            'username': log.username or 'anonymous',
            'user_id': log.user_id,
            'ip_address': log.ip_address,
            'action': log.action,
            'details': log.details,
            'task_id': log.task_id,
            'created_at': log.created_at.isoformat() if log.created_at else None
        })
    
    return jsonify({
        'logs': logs,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })
