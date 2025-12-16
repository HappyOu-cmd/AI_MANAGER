#!/usr/bin/env python3
"""
Админ панель - управление пользователями
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.db import db
from app.models.user import User
from app.models.activity_log import ActivityLog
from datetime import datetime

bp = Blueprint('admin', __name__, url_prefix='/admin')


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
    """Главная страница админ панели"""
    from app.models.document import Document
    
    # Статистика
    total_users = User.query.count()
    total_documents = Document.query.count()
    total_logs = ActivityLog.query.count()
    
    # Последние пользователи
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    return render_template(
        'admin/index.html',
        total_users=total_users,
        total_documents=total_documents,
        total_logs=total_logs,
        recent_users=recent_users
    )


@bp.route('/users')
@admin_required
def users():
    """Список всех пользователей"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = User.query.order_by(User.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users_list = pagination.items
    
    return render_template(
        'admin/users.html',
        users=users_list,
        pagination=pagination
    )


@bp.route('/register', methods=['GET', 'POST'])
@admin_required
def register_user():
    """Регистрация нового пользователя администратором"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        is_admin = bool(request.form.get('is_admin'))
        
        # Валидация
        if not username or not email or not password:
            flash('Все поля обязательны для заполнения', 'error')
            return render_template('admin/register.html')
        
        if password != password_confirm:
            flash('Пароли не совпадают', 'error')
            return render_template('admin/register.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return render_template('admin/register.html')
        
        # Проверка существования пользователя
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('admin/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return render_template('admin/register.html')
        
        # Создание пользователя
        user = User(username=username, email=email, is_admin=is_admin)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Логируем регистрацию
            log_activity(
                user_id=current_user.id,
                username=current_user.username,
                ip_address=request.remote_addr,
                action='admin_register',
                details=f'Администратор {current_user.username} зарегистрировал пользователя {username}'
            )
            
            flash(f'Пользователь {username} успешно зарегистрирован', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка регистрации: {str(e)}', 'error')
            return render_template('admin/register.html')
    
    return render_template('admin/register.html')


def log_activity(user_id=None, username=None, ip_address=None, action='', details='', task_id=None):
    """Вспомогательная функция для логирования активности"""
    try:
        log_entry = ActivityLog(
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            action=action,
            details=details,
            task_id=task_id
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"⚠️  Ошибка логирования активности: {e}")

