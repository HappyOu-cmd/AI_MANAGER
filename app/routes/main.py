#!/usr/bin/env python3
"""
Главные маршруты приложения
"""

from flask import Blueprint, render_template

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@bp.route('/health')
def health():
    """Проверка работоспособности"""
    from flask import jsonify
    return jsonify({'status': 'ok'})

