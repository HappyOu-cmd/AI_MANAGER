#!/usr/bin/env python3
"""
Маршруты для обработки ТЗ - можно создать несколько страниц для разных типов обработки
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
from pathlib import Path
import sys
import uuid

# Добавляем путь к src для импорта старых модулей
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from document_converter import DocumentConverter
from scenario_manager import ScenarioManager
from scenario_executor import ScenarioExecutor
from processing_status import ProcessingStatus

bp = Blueprint('processing', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

def allowed_file(filename):
    """Проверяет, разрешен ли формат файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/processing/tokarny')
def processing_tokarny():
    """Страница обработки токарных станков"""
    scenario_manager = ScenarioManager()
    scenarios = [s for s in scenario_manager.list_scenarios() if s.get('machine_type') == 'токарный']
    return render_template('processing_tokarny.html', scenarios=scenarios)


@bp.route('/processing/frezerny')
def processing_frezerny():
    """Страница обработки фрезерных станков"""
    scenario_manager = ScenarioManager()
    scenarios = [s for s in scenario_manager.list_scenarios() if s.get('machine_type') == 'фрезерный']
    return render_template('processing_frezerny.html', scenarios=scenarios)


@bp.route('/processing/universal')
def processing_universal():
    """Страница универсальной обработки"""
    scenario_manager = ScenarioManager()
    scenarios = scenario_manager.list_scenarios()
    return render_template('processing_universal.html', scenarios=scenarios)


# Можно добавить отдельные маршруты для загрузки для каждой страницы
# Или использовать общий /upload с параметром page_type

