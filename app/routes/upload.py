#!/usr/bin/env python3
"""
Маршруты для загрузки и обработки файлов
"""

from flask import Blueprint, request, jsonify, current_app
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

bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

def allowed_file(filename):
    """Проверяет, разрешен ли формат файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки, конвертации и заполнения ТЗ через ИИ"""
    current_app.logger.info("📥 Получен запрос /upload")
    
    if 'file' not in request.files:
        current_app.logger.warning("❌ Файл не найден в запросе")
        return jsonify({'error': 'Файл не выбран'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        current_app.logger.warning("❌ Имя файла пустое")
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not allowed_file(file.filename):
        current_app.logger.warning(f"❌ Неподдерживаемый формат: {file.filename}")
        return jsonify({
            'error': f'Неподдерживаемый формат. Разрешены: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400
    
    try:
        # Получаем task_id из запроса (генерируется на клиенте) или создаем новый
        task_id = request.form.get('task_id')
        current_app.logger.info(f"📋 Task ID: {task_id}")
        
        if not task_id:
            task_id = str(uuid.uuid4())
            current_app.logger.info(f"📋 Создан новый Task ID: {task_id}")
        
        status_manager = ProcessingStatus()
        status_manager.create_status(task_id)
        current_app.logger.info(f"✅ Статус создан для task_id: {task_id}")
        
        try:
            # Шаг 1: Сохраняем загруженный файл
            # Используем task_id для уникальности имен файлов при параллельной обработке
            current_app.logger.info("📁 Шаг 1: Сохранение файла...")
            status_manager.update_status(task_id, stage='file_upload', message='Сохранение файла...')
            original_filename = secure_filename(file.filename)
            # Добавляем task_id для уникальности при параллельной обработке
            filename = f"{task_id}_{original_filename}"
            upload_path = Path(current_app.config['UPLOAD_FOLDER']) / filename
            file.save(str(upload_path))
            current_app.logger.info(f"✅ Файл сохранен: {upload_path}")
            
            # Шаг 2: Конвертируем документ в текст
            current_app.logger.info("🔄 Шаг 2: Конвертация документа...")
            status_manager.update_status(task_id, stage='conversion', message='Конвертация документа в текст...')
            converter = DocumentConverter()
            # Используем task_id для уникальности имен конвертированных файлов
            converted_filename = f"{task_id}_{Path(original_filename).stem}_converted.txt"
            converted_path = converter.convert(
                str(upload_path),
                str(Path(current_app.config['OUTPUT_FOLDER']) / converted_filename)
            )
            current_app.logger.info(f"✅ Документ сконвертирован: {converted_path}")
            
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
            # Используем task_id в output_prefix для уникальности при параллельной обработке
            output_prefix = f"{task_id}_{Path(original_filename).stem}"
            result = executor.execute(
                converted_text,
                ai_provider=ai_provider,
                output_prefix=output_prefix
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
        
        current_app.logger.error(f"Ошибка обработки: {e}", exc_info=True)
        return jsonify({
            'error': f'Ошибка обработки: {str(e)}',
            'stage': 'conversion',
            'task_id': task_id
        }), 500


@bp.route('/api/status/<task_id>', methods=['GET'])
def api_get_status(task_id):
    """API: Получить статус обработки задачи"""
    status_manager = ProcessingStatus()
    status = status_manager.get_status(task_id)
    
    if not status:
        return jsonify({'error': 'Задача не найдена'}), 404
    
    return jsonify(status)
