#!/usr/bin/env python3
"""
Главные маршруты приложения
"""

from flask import Blueprint, render_template
from flask_login import current_user
import sys
from pathlib import Path

# Добавляем путь к src для импорта старых модулей
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from scenario_manager import ScenarioManager

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Главная страница"""
    from flask_login import login_required
    
    # Если пользователь не авторизован, показываем страницу с требованием входа
    if not current_user.is_authenticated:
        return render_template('index.html', scenarios=[], current_user=current_user, require_login=True)
    
    scenario_manager = ScenarioManager()
    scenarios = scenario_manager.list_scenarios()
    return render_template('index.html', scenarios=scenarios, current_user=current_user, require_login=False)


@bp.route('/health')
def health():
    """Проверка работоспособности"""
    from flask import jsonify
    return jsonify({'status': 'ok'})

