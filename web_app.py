#!/usr/bin/env python3
"""
Веб-интерфейс для конвертации документов и заполнения ТЗ через ИИ
Запуск: python web_app.py
"""

from flask import Flask, render_template, request, send_file, jsonify, flash
from werkzeug.utils import secure_filename
import os
import json
from pathlib import Path
import sys

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from document_converter import DocumentConverter
from prompt_builder import PromptBuilder
from ai_client import OpenAIClient, JayFlowClient
from json_to_excel import JSONToExcelConverter
from scenario_manager import ScenarioManager
from scenario_executor import ScenarioExecutor
from processing_status import ProcessingStatus
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'converted'
app.config['RESULTS_FOLDER'] = 'results'

# Создаем папки для загрузок и результатов
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
Path(app.config['OUTPUT_FOLDER']).mkdir(exist_ok=True)
Path(app.config['RESULTS_FOLDER']).mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

def allowed_file(filename):
    """Проверяет, разрешен ли формат файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Главная страница"""
    # Загружаем список сценариев
    scenario_manager = ScenarioManager()
    scenarios = scenario_manager.list_scenarios()
    return render_template('index.html', scenarios=scenarios)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки, конвертации и заполнения ТЗ через ИИ"""
    print(f"📥 Получен запрос /upload")
    
    if 'file' not in request.files:
        print("❌ Файл не найден в запросе")
        return jsonify({'error': 'Файл не выбран'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        print("❌ Имя файла пустое")
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not allowed_file(file.filename):
        print(f"❌ Неподдерживаемый формат: {file.filename}")
        return jsonify({
            'error': f'Неподдерживаемый формат. Разрешены: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400
    
    try:
        # Получаем task_id из запроса (генерируется на клиенте) или создаем новый
        task_id = request.form.get('task_id')
        print(f"📋 Task ID: {task_id}")
        
        if not task_id:
            task_id = str(uuid.uuid4())
            print(f"📋 Создан новый Task ID: {task_id}")
        
        status_manager = ProcessingStatus()
        status_manager.create_status(task_id)
        print(f"✅ Статус создан для task_id: {task_id}")
        
        try:
            # Шаг 1: Сохраняем загруженный файл
            print(f"📁 Шаг 1: Сохранение файла...")
            status_manager.update_status(task_id, stage='file_upload', message='Сохранение файла...')
            filename = secure_filename(file.filename)
            upload_path = Path(app.config['UPLOAD_FOLDER']) / filename
            file.save(str(upload_path))
            print(f"✅ Файл сохранен: {upload_path}")
            
            # Шаг 2: Конвертируем документ в текст
            print(f"🔄 Шаг 2: Конвертация документа...")
            status_manager.update_status(task_id, stage='conversion', message='Конвертация документа в текст...')
            converter = DocumentConverter()
            converted_filename = f"{Path(filename).stem}_converted.txt"
            converted_path = converter.convert(
                str(upload_path),
                str(Path(app.config['OUTPUT_FOLDER']) / converted_filename)
            )
            print(f"✅ Документ сконвертирован: {converted_path}")
            
            # Читаем сконвертированный текст
            with open(converted_path, 'r', encoding='utf-8') as f:
                converted_text = f.read()
            
            status_manager.update_status(
                task_id,
                message=f'Документ сконвертирован ({len(converted_text):,} символов)',
                metrics={'converted_text_size': len(converted_text)}
            )
            
            # Шаг 3: Получаем сценарий
            scenario_id = request.form.get('scenario_id', 'tokarny_default')
            scenario_manager = ScenarioManager()
            scenario = scenario_manager.get_scenario(scenario_id)
            
            if not scenario:
                status_manager.update_status(task_id, status='error', message=f'Сценарий не найден: {scenario_id}')
                return jsonify({
                    'error': f'Сценарий не найден: {scenario_id}',
                    'task_id': task_id
                }), 400
            
            # Шаг 4: Выполняем сценарий
            # Получаем выбор AI из запроса
            ai_provider = request.form.get('ai_provider', 'openai').lower()
            
            executor = ScenarioExecutor(scenario, status_manager=status_manager, task_id=task_id)
            result = executor.execute(
                converted_text,
                ai_provider=ai_provider,
                output_prefix=Path(filename).stem
            )
            
            if not result['success']:
                status_manager.update_status(
                    task_id,
                    status='error',
                    message=f'Ошибки: {"; ".join(result["errors"])}'
                )
                return jsonify({
                    'error': f'Ошибка выполнения сценария: {"; ".join(result["errors"])}',
                    'stage': 'ai_processing',
                    'task_id': task_id
                }), 500
            
            # Получаем финальный статус с метриками
            final_status = status_manager.get_status(task_id)
            
            # Формируем ответ с результатами
            response_data = {
                'success': True,
                'message': 'ТЗ успешно обработано',
                'task_id': task_id,
                'metrics': final_status.get('metrics', {}) if final_status else {},
                'results': {}
            }
            
            # Основной результат (JSON + Excel)
            sheets_added = []
            if 'main' in result['results']:
                main_result = result['results']['main']
                response_data['results']['main'] = {
                    'json_file': main_result['json_file'],
                    'json_size': main_result['json_size'],
                    'json_url': f'/download_result/{main_result["json_file"]}',
                    'excel_file': main_result.get('excel_file'),
                    'excel_size': main_result.get('excel_size', 0),
                    'excel_url': f'/download_result/{main_result["excel_file"]}' if main_result.get('excel_file') else None,
                    'sheets': [],  # Список добавленных листов
                    'usage': main_result.get('usage', {})
                }
            
            # Дополнительные результаты (CSV → Excel листы)
            sheet_names_map = {
                'instrument': 'Инструмент',
                'tooling': 'Оснастка',
                'services': 'Услуги',
                'spare_parts': 'ЗИП'
            }
            
            for result_type in ['instrument', 'tooling', 'services', 'spare_parts']:
                if result_type in result['results']:
                    sheet_result = result['results'][result_type]
                    if sheet_result.get('sheet_added'):
                        sheets_added.append(sheet_result['sheet_name'])
                        # Добавляем информацию о листе в основной результат
                        if 'main' in response_data['results']:
                            response_data['results']['main']['sheets'].append(sheet_result['sheet_name'])
            
            # Удаляем статус после успешного завершения
            status_manager.delete_status(task_id)
            
            return jsonify(response_data)
        
        except ValueError as e:
            if 'task_id' in locals():
                status_manager.update_status(task_id, status='error', message=str(e))
            return jsonify({
                'error': str(e),
                'stage': 'ai_setup',
                'task_id': task_id if 'task_id' in locals() else None
            }), 500
            # Ошибка с API ключом
            return jsonify({
                'error': str(e),
                'stage': 'ai_setup'
            }), 500
        except ImportError as e:
            if 'task_id' in locals():
                status_manager.update_status(task_id, status='error', message=str(e))
            return jsonify({
                'error': str(e),
                'stage': 'ai_setup',
                'task_id': task_id if 'task_id' in locals() else None
            }), 500
        except Exception as e:
            if 'task_id' in locals():
                status_manager.update_status(task_id, status='error', message=str(e))
            return jsonify({
                'error': f'Ошибка обработки ИИ: {str(e)}',
                'stage': 'ai_processing',
                'task_id': task_id if 'task_id' in locals() else None
            }), 500
    
    except Exception as e:
        # Пытаемся получить task_id если он был создан
        task_id = None
        if 'task_id' in locals():
            task_id = locals()['task_id']
            if task_id and 'status_manager' in locals():
                status_manager.update_status(task_id, status='error', message=str(e))
        
        return jsonify({
            'error': f'Ошибка обработки: {str(e)}',
            'stage': 'conversion',
            'task_id': task_id
        }), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Скачивание сконвертированного текстового файла"""
    file_path = Path(app.config['OUTPUT_FOLDER']) / secure_filename(filename)
    
    if not file_path.exists():
        return jsonify({'error': 'Файл не найден'}), 404
    
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=filename,
        mimetype='text/plain'
    )

@app.route('/download_result/<filename>')
def download_result(filename):
    """Скачивание заполненного JSON или Excel файла"""
    file_path = Path(app.config['RESULTS_FOLDER']) / secure_filename(filename)
    
    if not file_path.exists():
        return jsonify({'error': 'Файл не найден'}), 404
    
    # Определяем MIME тип по расширению
    if filename.endswith('.xlsx'):
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif filename.endswith('.json'):
        mimetype = 'application/json'
    elif filename.endswith('.docx'):
        mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    else:
        mimetype = 'application/octet-stream'
    
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )

@app.route('/scenarios')
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

@app.route('/api/scenarios', methods=['GET'])
def api_list_scenarios():
    """API: Список всех сценариев"""
    scenario_manager = ScenarioManager()
    scenarios = scenario_manager.list_scenarios()
    return jsonify(scenarios)

@app.route('/api/scenarios/<scenario_id>', methods=['GET'])
def api_get_scenario(scenario_id):
    """API: Получить сценарий"""
    scenario_manager = ScenarioManager()
    scenario = scenario_manager.get_scenario(scenario_id)
    
    if not scenario:
        return jsonify({'error': 'Сценарий не найден'}), 404
    
    return jsonify(scenario)

@app.route('/api/scenarios', methods=['POST'])
def api_create_scenario():
    """API: Создать сценарий"""
    try:
        scenario_data = request.get_json()
        scenario_manager = ScenarioManager()
        scenario = scenario_manager.create_scenario(scenario_data)
        return jsonify(scenario), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/scenarios/<scenario_id>', methods=['PUT'])
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

@app.route('/api/scenarios/<scenario_id>', methods=['DELETE'])
def api_delete_scenario(scenario_id):
    """API: Удалить сценарий"""
    scenario_manager = ScenarioManager()
    success = scenario_manager.delete_scenario(scenario_id)
    
    if not success:
        return jsonify({'error': 'Сценарий не найден'}), 404
    
    return jsonify({'success': True})

@app.route('/api/prompts', methods=['GET'])
def api_list_prompts():
    """API: Список доступных промптов"""
    machine_type = request.args.get('machine_type')
    scenario_manager = ScenarioManager()
    prompts = scenario_manager.list_available_prompts(machine_type)
    return jsonify(prompts)

@app.route('/api/templates', methods=['GET'])
def api_list_templates():
    """API: Список доступных шаблонов"""
    scenario_manager = ScenarioManager()
    templates = scenario_manager.list_available_templates()
    return jsonify(templates)

@app.route('/api/glossaries', methods=['GET'])
def api_list_glossaries():
    """API: Список доступных глоссариев"""
    scenario_manager = ScenarioManager()
    glossaries = scenario_manager.list_available_glossaries()
    return jsonify(glossaries)

@app.route('/api/status/<task_id>', methods=['GET'])
def api_get_status(task_id):
    """API: Получить статус обработки задачи"""
    status_manager = ProcessingStatus()
    status = status_manager.get_status(task_id)
    
    if not status:
        return jsonify({'error': 'Задача не найдена'}), 404
    
    return jsonify(status)

@app.route('/health')
def health():
    """Проверка работоспособности"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("=" * 60)
    print("🌐 Веб-интерфейс для заполнения ТЗ через ИИ")
    print("=" * 60)
    print("📂 Загрузки: uploads/")
    print("📄 Конвертированные: converted/")
    print("✅ Результаты: results/")
    print("🌍 Откройте в браузере: http://127.0.0.1:5000")
    print()
    
    # Проверка API ключа
    api_key = None
    
    # Сначала пробуем прочитать из файла
    api_key_file = Path(__file__).parent / 'key.txt'
    if api_key_file.exists():
        try:
            with open(api_key_file, 'r', encoding='utf-8') as f:
                api_key = f.read().strip()
            if api_key:
                print(f"✅ OpenAI API ключ найден в key.txt (первые 10 символов: {api_key[:10]}...)")
        except Exception as e:
            print(f"⚠️  Ошибка чтения key.txt: {e}")
    
    # Если не нашли в файле, пробуем переменную окружения
    if not api_key:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            print(f"✅ OpenAI API ключ найден в переменной окружения (первые 10 символов: {api_key[:10]}...)")
        else:
            print("⚠️  API ключ не найден!")
            print("   Создайте файл ApiKey.txt в корне проекта или установите:")
            print("   export OPENAI_API_KEY='your-key-here'")
    
    print("=" * 60)
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)

