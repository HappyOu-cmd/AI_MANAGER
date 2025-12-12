#!/usr/bin/env python3
"""
Маршруты для управления сценариями обработки ТЗ
"""

from flask import Blueprint, render_template, request, jsonify
import sys
from pathlib import Path

# Добавляем путь к src для импорта старых модулей
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from scenario_manager import ScenarioManager

bp = Blueprint('scenarios', __name__)


@bp.route('/scenarios')
def scenarios_page():
    """Страница управления сценариями"""
    scenario_manager = ScenarioManager()
    scenarios = scenario_manager.list_scenarios()
    
    # Получаем доступные промпты, шаблоны и глоссарии
    available_prompts = scenario_manager.list_available_prompts()
    available_templates = scenario_manager.list_available_templates()
    available_glossaries = scenario_manager.list_available_glossaries()
    
    return render_template('scenarios.html',
                          scenarios=scenarios,
                          available_prompts=available_prompts,
                          available_templates=available_templates,
                          available_glossaries=available_glossaries)


@bp.route('/api/scenarios', methods=['GET'])
def api_list_scenarios():
    """API: Список всех сценариев"""
    scenario_manager = ScenarioManager()
    scenarios = scenario_manager.list_scenarios()
    return jsonify(scenarios)


@bp.route('/api/scenarios/<scenario_id>', methods=['GET'])
def api_get_scenario(scenario_id):
    """API: Получить сценарий"""
    scenario_manager = ScenarioManager()
    scenario = scenario_manager.get_scenario(scenario_id)
    
    if not scenario:
        return jsonify({'error': 'Сценарий не найден'}), 404
    
    return jsonify(scenario)


@bp.route('/api/scenarios', methods=['POST'])
def api_create_scenario():
    """API: Создать сценарий"""
    try:
        scenario_data = request.get_json()
        scenario_manager = ScenarioManager()
        scenario = scenario_manager.create_scenario(scenario_data)
        return jsonify(scenario), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/api/scenarios/<scenario_id>', methods=['PUT'])
def api_update_scenario(scenario_id):
    """API: Обновить сценарий"""
    try:
        scenario_data = request.get_json()
        scenario_manager = ScenarioManager()
        scenario = scenario_manager.update_scenario(scenario_id, scenario_data)
        
        if not scenario:
            return jsonify({'error': 'Сценарий не найден'}), 404
        
        return jsonify(scenario)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/api/scenarios/<scenario_id>', methods=['DELETE'])
def api_delete_scenario(scenario_id):
    """API: Удалить сценарий"""
    scenario_manager = ScenarioManager()
    success = scenario_manager.delete_scenario(scenario_id)
    
    if not success:
        return jsonify({'error': 'Сценарий не найден'}), 404
    
    return jsonify({'success': True})


@bp.route('/api/prompts', methods=['GET'])
def api_list_prompts():
    """API: Список доступных промптов"""
    machine_type = request.args.get('machine_type')
    scenario_manager = ScenarioManager()
    prompts = scenario_manager.list_available_prompts(machine_type)
    return jsonify(prompts)


@bp.route('/api/templates', methods=['GET'])
def api_list_templates():
    """API: Список доступных шаблонов"""
    scenario_manager = ScenarioManager()
    templates = scenario_manager.list_available_templates()
    return jsonify(templates)


@bp.route('/api/glossaries', methods=['GET'])
def api_list_glossaries():
    """API: Список доступных глоссариев"""
    scenario_manager = ScenarioManager()
    glossaries = scenario_manager.list_available_glossaries()
    return jsonify(glossaries)

