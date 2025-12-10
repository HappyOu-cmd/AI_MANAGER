#!/usr/bin/env python3
"""
Модуль для выполнения сценариев обработки ТЗ
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent))

from prompt_builder import PromptBuilder
from ai_client import OpenAIClient, JayFlowClient
from json_to_excel import JSONToExcelConverter
try:
    from csv_to_excel import CSVToExcelAppender
except ImportError:
    CSVToExcelAppender = None


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
        
        # Инициализируем AI клиент
        if ai_provider == 'jayflow':
            ai_client = JayFlowClient()
        else:
            ai_client = OpenAIClient()
        
        # Обрабатываем основной промпт
        excel_path = None
        excel_filename = None
        current_step = 0
        
        if self.scenario['prompts']['main'].get('enabled'):
            current_step += 1
            if self.status_manager and self.task_id:
                self.status_manager.update_status(
                    self.task_id,
                    current_step=current_step,
                    stage='main_prompt',
                    message='Обработка основного промпта (технические характеристики)...',
                    progress=int((current_step / total_steps) * 100) if total_steps > 0 else 0
                )
            
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
                current_step += 1
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
            prompt_config = self.scenario['prompts']['main']
            prompt_file = self.project_root / prompt_config['file']
            tz_template = self.project_root / prompt_config['tz_template']
            glossary = self.project_root / prompt_config['glossary']
            
            # Строим промпт
            prompt_builder = PromptBuilder(
                prompt_file=str(prompt_file),
                tz_template_file=str(tz_template),
                glossary_file=str(glossary)
            )
            final_prompt = prompt_builder.build_prompt(converted_text)
            
            # Сохраняем размер промпта для метрик
            prompt_size = len(final_prompt)
            
            # Обновляем статус с размером промпта
            if self.status_manager and self.task_id:
                self.status_manager.update_status(
                    self.task_id,
                    message=f'Отправка промпта в AI ({prompt_size:,} символов)...',
                    metrics={'prompt_size': prompt_size}
                )
            
            # Отправляем в AI
            result = ai_client.process_prompt(final_prompt)
            
            if not result['success']:
                self.errors.append(f"Ошибка обработки основного промпта: {result.get('error')}")
                return None
            
            # Сохраняем JSON
            json_filename = f"{output_prefix}_filled.json"
            json_path = self.project_root / "results" / json_filename
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result['json'], f, ensure_ascii=False, indent=2)
            
            # Конвертируем в Excel
            excel_filename = f"{output_prefix}_filled.xlsx"
            excel_path = self.project_root / "results" / excel_filename
            
            try:
                excel_converter = JSONToExcelConverter()
                excel_converter.convert(result['json'], str(excel_path))
                excel_available = True
            except Exception as e:
                print(f"⚠️  Ошибка создания Excel файла: {e}")
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
            prompt_config = self.scenario['prompts'][prompt_type]
            prompt_file = self.project_root / prompt_config['file']
            
            if not prompt_file.exists():
                self.errors.append(f"Файл промпта не найден: {prompt_file}")
                return None
            
            # Читаем промпт
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            # Подставляем текст ТЗ (может быть несколько плейсхолдеров)
            final_prompt = prompt_template.replace('{текст ТЗ}', converted_text)
            # Также обрабатываем вариант без фигурных скобок
            final_prompt = final_prompt.replace('Текст ТЗ:', converted_text)
            final_prompt = final_prompt.replace('Текст ТЗ\n', converted_text + '\n')
            
            # Отправляем в AI (текстовый ответ, не JSON)
            result = ai_client.process_prompt_text(final_prompt)
            
            if not result['success']:
                self.errors.append(f"Ошибка обработки промпта {prompt_type}: {result.get('error')}")
                return None
            
            # Если нет Excel файла, создаем пустой
            if not excel_path or not Path(excel_path).exists():
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
            
            # Парсим CSV из ответа
            if CSVToExcelAppender is None:
                self.errors.append(f"CSVToExcelAppender не доступен для промпта {prompt_type}")
                return None
            
            csv_appender = CSVToExcelAppender()
            csv_text = csv_appender.parse_csv_from_text(result['text'])
            
            # Имена листов
            sheet_names = {
                'instrument': 'Инструмент',
                'tooling': 'Оснастка',
                'services': 'Услуги',
                'spare_parts': 'ЗИП'
            }
            
            # Добавляем лист в Excel
            try:
                csv_appender.add_csv_sheet(
                    excel_path,
                    csv_text,
                    sheet_names.get(prompt_type, prompt_type)
                )
                sheet_added = True
            except Exception as e:
                print(f"⚠️  Ошибка добавления листа {prompt_type}: {e}")
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

