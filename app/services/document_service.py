#!/usr/bin/env python3
"""
Сервис для обработки документов
Объединяет конвертацию, построение промпта и обработку ИИ
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

from app.core.converters.document import DocumentConverter
from app.core.builders.prompt_builder import PromptBuilder
from app.services.ai_service import AIService
from app.core.exporters.json_to_excel import JSONToExcelConverter
from app.utils.exceptions import DocumentConversionError, AIProcessingError


class DocumentService:
    """Сервис для полной обработки документа"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Конфигурация приложения
        """
        self.config = config
        self.converter = DocumentConverter()
        self.prompt_builder = PromptBuilder(
            prompt_file=str(config['PROMPT_TEMPLATE_FILE']),
            tz_template_file=str(config['TZ_TEMPLATE_FILE']),
            glossary_file=str(config['GLOSSARY_FILE'])
        )
        self.ai_service = AIService(config)
        self.excel_converter = JSONToExcelConverter()
    
    def process_document(self, file_path: str, ai_provider: str = 'openai') -> Dict[str, Any]:
        """
        Полная обработка документа: конвертация → промпт → ИИ → результат
        
        Args:
            file_path: Путь к загруженному файлу
            ai_provider: Провайдер ИИ ('openai' или 'jayflow')
            
        Returns:
            Словарь с результатом обработки
        """
        filename = Path(file_path).stem
        
        # Шаг 1: Конвертация документа
        try:
            converted_filename = f"{filename}_converted.txt"
            converted_path = Path(self.config['OUTPUT_FOLDER']) / converted_filename
            self.converter.convert(str(file_path), str(converted_path))
            
            # Читаем сконвертированный текст
            with open(converted_path, 'r', encoding='utf-8') as f:
                converted_text = f.read()
        except Exception as e:
            raise DocumentConversionError(f"Ошибка конвертации документа: {str(e)}")
        
        # Шаг 2: Построение промпта
        try:
            final_prompt = self.prompt_builder.build_prompt(converted_text)
        except Exception as e:
            raise DocumentConversionError(f"Ошибка построения промпта: {str(e)}")
        
        # Шаг 3: Обработка ИИ
        try:
            ai_result = self.ai_service.process_with_ai(final_prompt, ai_provider)
            
            if not ai_result['success']:
                raise AIProcessingError(
                    ai_result.get('error', 'Неизвестная ошибка обработки ИИ')
                )
        except Exception as e:
            if isinstance(e, AIProcessingError):
                raise
            raise AIProcessingError(f"Ошибка обработки ИИ: {str(e)}")
        
        # Шаг 4: Сохранение результата в JSON
        result_filename = f"{filename}_filled.json"
        result_path = Path(self.config['RESULTS_FOLDER']) / result_filename
        
        try:
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(ai_result['json'], f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise AIProcessingError(f"Ошибка сохранения результата: {str(e)}")
        
        # Шаг 5: Конвертация в Excel
        excel_filename = None
        excel_size = 0
        excel_available = False
        
        try:
            excel_filename = f"{filename}_filled.xlsx"
            excel_path = Path(self.config['RESULTS_FOLDER']) / excel_filename
            self.excel_converter.convert(ai_result['json'], str(excel_path))
            excel_size = os.path.getsize(excel_path)
            excel_available = True
        except Exception as e:
            # Excel не критичен, просто логируем
            import logging
            logging.warning(f"Ошибка создания Excel файла: {e}")
        
        # Формируем ответ
        usage_info = ai_result.get('usage', {})
        
        return {
            'success': True,
            'message': 'ТЗ успешно заполнено с помощью ИИ',
            'filename': result_filename,
            'size': os.path.getsize(result_path),
            'download_url': f'/download_result/{result_filename}',
            'excel_filename': excel_filename if excel_available else None,
            'excel_size': excel_size if excel_available else 0,
            'excel_download_url': f'/download_result/{excel_filename}' if excel_available else None,
            'usage': {
                'prompt_tokens': usage_info.get('prompt_tokens', 0),
                'completion_tokens': usage_info.get('completion_tokens', 0),
                'total_tokens': usage_info.get('total_tokens', 0)
            }
        }

