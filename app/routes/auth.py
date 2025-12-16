#!/usr/bin/env python3
"""
Маршруты для аутентификации (регистрация, вход, выход)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.db import db
from app.models.user import User
from app.models.activity_log import ActivityLog
from datetime import datetime

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Валидация
        if not username or not email or not password:
            flash('Все поля обязательны для заполнения', 'error')
            return render_template('auth/register.html')
        
        if password != password_confirm:
            flash('Пароли не совпадают', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return render_template('auth/register.html')
        
        # Проверка существования пользователя
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return render_template('auth/register.html')
        
        # Создание пользователя
        user = User(username=username, email=email)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Логируем регистрацию
            log_activity(
                user_id=user.id,
                username=user.username,
                ip_address=request.remote_addr,
                action='register',
                details=f'Регистрация пользователя {username}'
            )
            
            flash('Регистрация успешна! Теперь вы можете войти.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка регистрации: {str(e)}', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Вход в систему"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        if not username or not password:
            flash('Введите имя пользователя и пароль', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Логируем вход
            log_activity(
                user_id=user.id,
                username=user.username,
                ip_address=request.remote_addr,
                action='login',
                details=f'Вход пользователя {username}'
            )
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            # Логируем неудачную попытку входа
            log_activity(
                user_id=None,
                username=username,
                ip_address=request.remote_addr,
                action='login_failed',
                details=f'Неудачная попытка входа для {username}'
            )
            flash('Неверное имя пользователя или пароль', 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    username = current_user.username
    
    # Логируем выход
    log_activity(
        user_id=current_user.id,
        username=username,
        ip_address=request.remote_addr,
        action='logout',
        details=f'Выход пользователя {username}'
    )
    
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.index'))


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
        # Не прерываем выполнение при ошибке логирования
        print(f"⚠️  Ошибка логирования активности: {e}")
