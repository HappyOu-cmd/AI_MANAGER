#!/usr/bin/env python3
"""
Маршруты для загрузки и обработки файлов
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from pathlib import Path
import sys
import uuid
import re
from datetime import datetime

# Добавляем путь к src для импорта старых модулей
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from document_converter import DocumentConverter
from scenario_manager import ScenarioManager
from scenario_executor import ScenarioExecutor
from processing_status import ProcessingStatus
from app.models.db import db
from app.models.document import Document
from app.models.activity_log import ActivityLog

bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

def allowed_file(filename):
    """Проверяет, разрешен ли формат файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Обработка загрузки, конвертации и заполнения ТЗ через ИИ"""
    # Логируем начало обработки
    log_activity(
        user_id=current_user.id,
        username=current_user.username,
        ip_address=request.remote_addr,
        action='upload_start',
        details=f'Начало обработки файла'
    )
    
    current_app.logger.info(f"📥 Получен запрос /upload от пользователя {current_user.username}")
    
        if 'file' not in request.files:
        current_app.logger.warning("❌ Файл не найден в запросе")
        return jsonify({'error': 'Файл не выбран'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
        current_app.logger.warning("❌ Имя файла пустое")
        return jsonify({'error': 'Файл не выбран'}), 400
    
    # Проверяем расширение ДО применения secure_filename (который может удалить кириллицу)
    original_filename = file.filename
    if not allowed_file(original_filename):
        current_app.logger.warning(f"❌ Неподдерживаемый формат: {original_filename}")
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
            # Применяем secure_filename для безопасного имени, но сохраняем оригинальное для отображения
            safe_filename = secure_filename(original_filename)
            # Если secure_filename удалил все (кириллица), используем оригинальное имя с заменой небезопасных символов
            if not safe_filename or safe_filename == original_filename.rsplit('.', 1)[-1]:
                # Создаем безопасное имя вручную: заменяем пробелы и небезопасные символы
                name_part = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
                ext_part = original_filename.rsplit('.', 1)[-1] if '.' in original_filename else ''
                # Заменяем небезопасные символы на подчеркивания, но сохраняем кириллицу
                safe_name = re.sub(r'[^\w\s\-_\.]', '_', name_part)
                safe_name = re.sub(r'\s+', '_', safe_name)
                safe_filename = f"{safe_name}.{ext_part}" if ext_part else safe_name
            # Добавляем task_id для уникальности при параллельной обработке
            filename = f"{task_id}_{safe_filename}"
        upload_path = Path(current_app.config['UPLOAD_FOLDER']) / filename
        file.save(str(upload_path))
            current_app.logger.info(f"✅ Файл сохранен: {upload_path}")
        
            # Шаг 2: Конвертируем документ в текст
            current_app.logger.info("🔄 Шаг 2: Конвертация документа...")
            status_manager.update_status(task_id, stage='conversion', message='Конвертация документа в текст...')
            converter = DocumentConverter()
            # Используем task_id для уникальности имен конвертированных файлов
            # Используем safe_filename для имени конвертированного файла
            converted_filename = f"{task_id}_{Path(safe_filename).stem}_converted.txt"
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
            
            # Засекаем время начала обработки
            processing_start_time = datetime.utcnow()
            
            current_app.logger.info(f"[{task_id}] 🚀 Начало выполнения сценария '{scenario_id}' (AI: {ai_provider})")
            executor = ScenarioExecutor(scenario, status_manager=status_manager, task_id=task_id)
            # Используем task_id в output_prefix для уникальности при параллельной обработке
            output_prefix = f"{task_id}_{Path(safe_filename).stem}"
            result = executor.execute(
                converted_text,
                ai_provider=ai_provider,
                output_prefix=output_prefix
            )
            
            # Вычисляем время обработки
            processing_end_time = datetime.utcnow()
            processing_time = (processing_end_time - processing_start_time).total_seconds()
            
            current_app.logger.info(f"[{task_id}] ✅ Сценарий выполнен (success: {result['success']}, ошибок: {len(result['errors'])})")
            
            # Получаем финальный статус с метриками
            final_status = status_manager.get_status(task_id)
            metrics = final_status.get('metrics', {}) if final_status else {}
            
            # Основной результат (JSON + Excel)
            main_result = result['results'].get('main', {}) if result['success'] else {}
            json_file = main_result.get('json_file')
            excel_file = main_result.get('excel_file')
            
            # Сохраняем документ в базу данных
            doc = Document(
                user_id=current_user.id,
                task_id=task_id,
                original_filename=original_filename,
                scenario_id=scenario_id,
                ai_provider=ai_provider,
                json_file=json_file,
                excel_file=excel_file,
                json_size=main_result.get('json_size', 0),
                excel_size=main_result.get('excel_size', 0),
                prompt_size=metrics.get('prompt_size', 0),
                tokens_used=metrics.get('tokens_used', 0),
                processing_time=processing_time,
                status='completed' if result['success'] else 'error',
                error_message='; '.join(result['errors']) if result['errors'] else None,
                completed_at=processing_end_time if result['success'] else None
            )
            
            try:
                db.session.add(doc)
                db.session.commit()
                current_app.logger.info(f"[{task_id}] ✅ Документ сохранен в БД (ID: {doc.id})")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"[{task_id}] ❌ Ошибка сохранения в БД: {e}")
            
            if not result['success']:
                status_manager.update_status(
                    task_id,
                    status='error',
                    message=f'Ошибки: {"; ".join(result["errors"])}'
                )
                
                # Логируем ошибку
                log_activity(
                    user_id=current_user.id,
                    username=current_user.username,
                    ip_address=request.remote_addr,
                    action='upload_error',
                    details=f'Ошибка обработки: {"; ".join(result["errors"])}',
                    task_id=task_id
                )
                
                return jsonify({
                    'error': f'Ошибка выполнения сценария: {"; ".join(result["errors"])}',
                    'stage': 'ai_processing',
                    'task_id': task_id
                }), 500
            
            # Формируем ответ с результатами
            response_data = {
                'success': True,
                'message': 'ТЗ успешно обработано',
                'task_id': task_id,
                'document_id': doc.id,
                'metrics': metrics,
                'results': {}
            }
            
            # Основной результат (JSON + Excel)
            sheets_added = []
            if 'main' in result['results']:
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
            
            # Обновляем статус на "completed" перед возвратом ответа
            status_manager.update_status(
                task_id,
                status='completed',
                progress=100,
                message='Обработка завершена успешно'
            )
            
            # Очищаем старые статусы (старше 10 минут)
            status_manager.cleanup_old_statuses(max_age_minutes=10)
            
            # Логируем успешное завершение
            log_activity(
                user_id=current_user.id,
                username=current_user.username,
                ip_address=request.remote_addr,
                action='upload_completed',
                details=f'Обработка завершена успешно: {original_filename}',
                task_id=task_id
            )
            
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


@bp.route('/api/status/<task_id>/cancel', methods=['POST'])
@login_required
def api_cancel_task(task_id):
    """API: Остановить обработку задачи"""
    current_app.logger.info(f"🛑 Запрос на остановку задачи: {task_id} от пользователя {current_user.username}")
    
    # Проверяем, что задача принадлежит пользователю
    doc = Document.query.filter_by(task_id=task_id, user_id=current_user.id).first()
    if not doc:
        return jsonify({
            'success': False,
            'error': 'Задача не найдена или у вас нет прав на её отмену',
            'task_id': task_id
        }), 404
    
    status_manager = ProcessingStatus()
    success = status_manager.cancel_task(task_id)
    
    if success:
        # Обновляем статус в БД
        doc.status = 'cancelled'
        db.session.commit()
        
        # Логируем отмену
        log_activity(
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            action='upload_cancelled',
            details=f'Обработка отменена пользователем',
            task_id=task_id
        )
        
        current_app.logger.info(f"✅ Задача {task_id} успешно отменена")
        return jsonify({
            'success': True,
            'message': 'Задача успешно отменена',
            'task_id': task_id
        })
    else:
        current_app.logger.warning(f"⚠️ Не удалось отменить задачу: {task_id}")
        return jsonify({
            'success': False,
            'error': 'Задача не найдена или уже завершена',
            'task_id': task_id
        }), 404


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
        current_app.logger.warning(f"⚠️  Ошибка логирования активности: {e}")
