#!/usr/bin/env python3
"""
Главные маршруты приложения
"""

from flask import Blueprint, render_template
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
    scenario_manager = ScenarioManager()
    scenarios = scenario_manager.list_scenarios()
    return render_template('index.html', scenarios=scenarios)


@bp.route('/health')
def health():
    """Проверка работоспособности"""
    from flask import jsonify
    return jsonify({'status': 'ok'})

