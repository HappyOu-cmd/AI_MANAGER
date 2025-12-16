#!/usr/bin/env python3
"""
Модуль для выполнения сценариев обработки ТЗ
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys
import logging

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent))

from prompt_builder import PromptBuilder
from ai_client import OpenAIClient, JayFlowClient
from json_to_excel import JSONToExcelConverter
try:
    from csv_to_excel import CSVToExcelAppender
except ImportError:
    CSVToExcelAppender = None

# Настраиваем логирование
logger = logging.getLogger(__name__)


class ScenarioExecutor:
    """Выполняет сценарий обработки ТЗ"""
    
    def __init__(self, scenario: Dict, status_manager=None, task_id: str = None):
        """
        Инициализация исполнителя
        
        Args:
            scenario: Словарь с конфигурацией сценария
            status_manager: Менеджер статусов для отслеживания прогресса (опционально)
            task_id: ID задачи для отслеживания статуса (опционально)
        """
        self.scenario = scenario
        self.project_root = Path(__file__).parent.parent
        self.results = {}
        self.errors = []
        self.status_manager = status_manager
        self.task_id = task_id
    
    def execute(self, converted_text: str, ai_provider: str = 'openai', 
                output_prefix: str = "result") -> Dict[str, Any]:
        """
        Выполняет сценарий обработки
        
        Args:
            converted_text: Текст из сконвертированного документа
            ai_provider: Провайдер AI ('openai' или 'jayflow')
            output_prefix: Префикс для имен выходных файлов
        
        Returns:
            Словарь с результатами:
            {
                'success': bool,
                'results': {
                    'main': {...},  # JSON + Excel
                    'instrument': {...},  # CSV → Excel лист
                    ...
                },
                'errors': List[str]
            }
        """
        # Подсчитываем общее количество шагов
        total_steps = 0
        if self.scenario['prompts']['main'].get('enabled'):
            total_steps += 1
        additional_types = ['instrument', 'tooling', 'services', 'spare_parts']
        for prompt_type in additional_types:
            if self.scenario['prompts'][prompt_type].get('enabled'):
                total_steps += 1
        
        # Обновляем статус
        if self.status_manager and self.task_id:
            self.status_manager.update_status(
                self.task_id,
                status='processing',
                total_steps=total_steps,
                current_step=0,
                message='Инициализация обработки...'
            )
        
        # Проверяем, не отменена ли задача
        if self.status_manager and self.task_id:
            if self.status_manager.is_cancelled(self.task_id):
                logger.info(f"[{self.task_id}] ⛔ Задача отменена до начала обработки")
                return {
                    'success': False,
                    'results': {},
                    'errors': ['Задача отменена пользователем']
                }
        
        # Инициализируем AI клиент
        logger.info(f"[{self.task_id}] 🤖 Инициализация AI клиента: {ai_provider}")
        if ai_provider == 'jayflow':
            ai_client = JayFlowClient()
        else:
            ai_client = OpenAIClient()
        logger.info(f"[{self.task_id}] ✅ AI клиент инициализирован")
        
        # Обрабатываем основной промпт
        excel_path = None
        excel_filename = None
        current_step = 0
        
        if self.scenario['prompts']['main'].get('enabled'):
            current_step += 1
            logger.info(f"[{self.task_id}] 📝 Начало обработки основного промпта (шаг {current_step}/{total_steps})")
            if self.status_manager and self.task_id:
                self.status_manager.update_status(
                    self.task_id,
                    current_step=current_step,
                    stage='main_prompt',
                    message='Обработка основного промпта (технические характеристики)...',
                    progress=int((current_step / total_steps) * 100) if total_steps > 0 else 0
                )
            
            # Проверяем отмену перед обработкой
            if self.status_manager and self.task_id and self.status_manager.is_cancelled(self.task_id):
                logger.info(f"[{self.task_id}] ⛔ Задача отменена перед обработкой основного промпта")
                return {
                    'success': False,
                    'results': {},
                    'errors': ['Задача отменена пользователем']
                }
            
            result = self._process_main_prompt(converted_text, ai_client, output_prefix)
            if result:
                self.results['main'] = result
                # Сохраняем путь к Excel файлу для добавления дополнительных листов
                excel_path = result.get('excel_path')
                excel_filename = result.get('excel_file')
                
                # Обновляем метрики
                if self.status_manager and self.task_id:
                    usage = result.get('usage', {})
                    prompt_size = result.get('prompt_size', 0)
                    self.status_manager.update_status(
                        self.task_id,
                        metrics={
                            'prompt_size': prompt_size,
                            'tokens_used': usage.get('total_tokens', 0),
                            'prompt_tokens': usage.get('prompt_tokens', 0),
                            'completion_tokens': usage.get('completion_tokens', 0)
                        }
                    )
        
        # Обрабатываем дополнительные промпты (добавляем в тот же Excel)
        step_names = {
            'instrument': 'Извлечение инструмента',
            'tooling': 'Извлечение оснастки',
            'services': 'Извлечение услуг',
            'spare_parts': 'Извлечение ЗИП'
        }
        
        for prompt_type in additional_types:
            if self.scenario['prompts'][prompt_type].get('enabled'):
                # Проверяем отмену перед каждым промптом
                if self.status_manager and self.task_id and self.status_manager.is_cancelled(self.task_id):
                    logger.info(f"[{self.task_id}] ⛔ Задача отменена перед обработкой промпта {prompt_type}")
                    return {
                        'success': False,
                        'results': self.results,
                        'errors': self.errors + ['Задача отменена пользователем']
                    }
                
                current_step += 1
                logger.info(f"[{self.task_id}] 📝 Начало обработки промпта {prompt_type} (шаг {current_step}/{total_steps})")
                if self.status_manager and self.task_id:
                    self.status_manager.update_status(
                        self.task_id,
                        current_step=current_step,
                        stage=f'{prompt_type}_prompt',
                        message=f'{step_names.get(prompt_type, prompt_type)}...',
                        progress=int((current_step / total_steps) * 100) if total_steps > 0 else 0
                    )
                
                # Если Excel еще не создан, используем имя файла из основного результата или создаем новое
                if not excel_path:
                    if excel_filename:
                        excel_path = str(self.project_root / "results" / excel_filename)
                    else:
                        excel_filename = f"{output_prefix}_filled.xlsx"
                        excel_path = str(self.project_root / "results" / excel_filename)
                
                result = self._process_additional_prompt(
                    prompt_type, converted_text, ai_client, output_prefix, excel_path
                )
                if result:
                    self.results[prompt_type] = result
                    # Обновляем размер Excel файла в основном результате
                    if 'main' in self.results and excel_path and Path(excel_path).exists():
                        self.results['main']['excel_size'] = Path(excel_path).stat().st_size
        
        # Финальный статус
        if self.status_manager and self.task_id:
            self.status_manager.update_status(
                self.task_id,
                status='completed' if len(self.errors) == 0 else 'error',
                current_step=total_steps,
                progress=100,
                message='Обработка завершена' if len(self.errors) == 0 else f'Ошибки: {len(self.errors)}'
            )
        
        return {
            'success': len(self.errors) == 0,
            'results': self.results,
            'errors': self.errors
        }
    
    def _process_main_prompt(self, converted_text: str, ai_client, output_prefix: str) -> Optional[Dict]:
        """Обрабатывает основной промпт (JSON + Excel)"""
        try:
            logger.info(f"[{self.task_id}] 📋 Чтение конфигурации основного промпта")
            prompt_config = self.scenario['prompts']['main']
            prompt_file = self.project_root / prompt_config['file']
            tz_template = self.project_root / prompt_config['tz_template']
            glossary = self.project_root / prompt_config['glossary']
            
            logger.info(f"[{self.task_id}] 🔨 Построение промпта (файл: {prompt_file.name})")
            # Строим промпт
            prompt_builder = PromptBuilder(
                prompt_file=str(prompt_file),
                tz_template_file=str(tz_template),
                glossary_file=str(glossary)
            )
            final_prompt = prompt_builder.build_prompt(converted_text)
            
            # Сохраняем размер промпта для метрик
            prompt_size = len(final_prompt)
            logger.info(f"[{self.task_id}] ✅ Промпт построен: {prompt_size:,} символов (~{prompt_size // 4:,} токенов)")
            
            # Обновляем статус с размером промпта
            if self.status_manager and self.task_id:
                self.status_manager.update_status(
                    self.task_id,
                    message=f'Отправка промпта в AI ({prompt_size:,} символов)...',
                    metrics={'prompt_size': prompt_size}
                )
            
            # Проверяем отмену перед отправкой
            if self.status_manager and self.task_id and self.status_manager.is_cancelled(self.task_id):
                logger.info(f"[{self.task_id}] ⛔ Задача отменена перед отправкой основного промпта")
                return None
            
            # Отправляем в AI
            logger.info(f"[{self.task_id}] 🚀 Отправка основного промпта в AI...")
            result = ai_client.process_prompt(final_prompt)
            logger.info(f"[{self.task_id}] 📥 Получен ответ от AI (success: {result.get('success')})")
            
            if not result['success']:
                error_msg = result.get('error', 'Неизвестная ошибка')
                logger.error(f"[{self.task_id}] ❌ Ошибка обработки основного промпта: {error_msg}")
                self.errors.append(f"Ошибка обработки основного промпта: {error_msg}")
                return None
            
            logger.info(f"[{self.task_id}] 💾 Сохранение JSON результата...")
            # Сохраняем JSON
            json_filename = f"{output_prefix}_filled.json"
            json_path = self.project_root / "results" / json_filename
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result['json'], f, ensure_ascii=False, indent=2)
            logger.info(f"[{self.task_id}] ✅ JSON сохранен: {json_path.name} ({json_path.stat().st_size:,} байт)")
            
            # Конвертируем в Excel
            logger.info(f"[{self.task_id}] 📊 Конвертация в Excel...")
            excel_filename = f"{output_prefix}_filled.xlsx"
            excel_path = self.project_root / "results" / excel_filename
            
            try:
                excel_converter = JSONToExcelConverter()
                excel_converter.convert(result['json'], str(excel_path))
                excel_available = True
                logger.info(f"[{self.task_id}] ✅ Excel создан: {excel_path.name} ({excel_path.stat().st_size:,} байт)")
            except Exception as e:
                logger.error(f"[{self.task_id}] ⚠️  Ошибка создания Excel файла: {e}")
                excel_available = False
                excel_path = None
            
            return {
                'json_file': json_filename,
                'json_path': str(json_path),
                'json_size': json_path.stat().st_size,
                'excel_file': excel_filename if excel_available else None,
                'excel_path': str(excel_path) if excel_available else None,
                'excel_size': excel_path.stat().st_size if excel_available else 0,
                'usage': result.get('usage', {}),
                'prompt_size': prompt_size
            }
        
        except Exception as e:
            self.errors.append(f"Ошибка обработки основного промпта: {str(e)}")
            return None
    
    def _process_additional_prompt(self, prompt_type: str, converted_text: str, 
                                   ai_client, output_prefix: str, excel_path: Optional[str] = None) -> Optional[Dict]:
        """Обрабатывает дополнительный промпт (CSV → Excel лист)"""
        try:
            logger.info(f"[{self.task_id}] 📋 Чтение конфигурации промпта {prompt_type}")
            prompt_config = self.scenario['prompts'][prompt_type]
            prompt_file = self.project_root / prompt_config['file']
            
            if not prompt_file.exists():
                error_msg = f"Файл промпта не найден: {prompt_file}"
                logger.error(f"[{self.task_id}] ❌ {error_msg}")
                self.errors.append(error_msg)
                return None
            
            logger.info(f"[{self.task_id}] 📖 Чтение шаблона промпта: {prompt_file.name}")
            # Читаем промпт
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            # Подставляем текст ТЗ (может быть несколько плейсхолдеров)
            final_prompt = prompt_template.replace('{текст ТЗ}', converted_text)
            # Также обрабатываем вариант без фигурных скобок
            final_prompt = final_prompt.replace('Текст ТЗ:', converted_text)
            final_prompt = final_prompt.replace('Текст ТЗ\n', converted_text + '\n')
            
            prompt_size = len(final_prompt)
            logger.info(f"[{self.task_id}] ✅ Промпт {prompt_type} подготовлен: {prompt_size:,} символов (~{prompt_size // 4:,} токенов)")
            
            # Проверяем отмену перед отправкой
            if self.status_manager and self.task_id and self.status_manager.is_cancelled(self.task_id):
                logger.info(f"[{self.task_id}] ⛔ Задача отменена перед отправкой промпта {prompt_type}")
                return None
            
            # Отправляем в AI (текстовый ответ, не JSON)
            logger.info(f"[{self.task_id}] 🚀 Отправка промпта {prompt_type} в AI...")
            result = ai_client.process_prompt_text(final_prompt)
            logger.info(f"[{self.task_id}] 📥 Получен ответ от AI для {prompt_type} (success: {result.get('success')})")
            
            if not result['success']:
                error_msg = result.get('error', 'Неизвестная ошибка')
                logger.error(f"[{self.task_id}] ❌ Ошибка обработки промпта {prompt_type}: {error_msg}")
                self.errors.append(f"Ошибка обработки промпта {prompt_type}: {error_msg}")
                return None
            
            logger.info(f"[{self.task_id}] 📄 Парсинг CSV из ответа для {prompt_type}...")
            response_text = result.get('text', '')
            logger.info(f"[{self.task_id}] 📏 Размер ответа: {len(response_text):,} символов")
            
            # Если нет Excel файла, создаем пустой
            if not excel_path or not Path(excel_path).exists():
                logger.info(f"[{self.task_id}] 📊 Создание нового Excel файла...")
                from openpyxl import Workbook
                excel_filename = f"{output_prefix}_filled.xlsx"
                excel_path = self.project_root / "results" / excel_filename
                excel_path.parent.mkdir(parents=True, exist_ok=True)
                
                wb = Workbook()
                # Удаляем дефолтный лист если он пустой
                if len(wb.sheetnames) == 1:
                    wb.remove(wb.active)
                wb.save(str(excel_path))
                excel_path = str(excel_path)
                logger.info(f"[{self.task_id}] ✅ Excel файл создан: {excel_path}")
            
            # Парсим CSV из ответа
            if CSVToExcelAppender is None:
                error_msg = f"CSVToExcelAppender не доступен для промпта {prompt_type}"
                logger.error(f"[{self.task_id}] ❌ {error_msg}")
                self.errors.append(error_msg)
                return None
            
            csv_appender = CSVToExcelAppender()
            csv_text = csv_appender.parse_csv_from_text(result['text'])
            logger.info(f"[{self.task_id}] ✅ CSV распарсен: {len(csv_text):,} символов")
            
            # Имена листов
            sheet_names = {
                'instrument': 'Инструмент',
                'tooling': 'Оснастка',
                'services': 'Услуги',
                'spare_parts': 'ЗИП'
            }
            
            # Добавляем лист в Excel
            logger.info(f"[{self.task_id}] 📊 Добавление листа '{sheet_names.get(prompt_type, prompt_type)}' в Excel...")
            try:
                csv_appender.add_csv_sheet(
                    excel_path,
                    csv_text,
                    sheet_names.get(prompt_type, prompt_type)
                )
                sheet_added = True
                logger.info(f"[{self.task_id}] ✅ Лист '{sheet_names.get(prompt_type, prompt_type)}' успешно добавлен")
            except Exception as e:
                logger.error(f"[{self.task_id}] ⚠️  Ошибка добавления листа {prompt_type}: {e}")
                import traceback
                traceback.print_exc()
                sheet_added = False
            
            return {
                'sheet_added': sheet_added,
                'sheet_name': sheet_names.get(prompt_type, prompt_type),
                'usage': result.get('usage', {})
            }
        
        except Exception as e:
            self.errors.append(f"Ошибка обработки промпта {prompt_type}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

