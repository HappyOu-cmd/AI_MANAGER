#!/usr/bin/env python3
"""
OpenAI API клиент
Наследуется от базового класса BaseAIClient
"""

import os
import json
import time
from typing import Optional, Dict, Any
import re
from pathlib import Path
from datetime import datetime

from app.core.ai.base import BaseAIClient


class OpenAIClient(BaseAIClient):
    """Клиент для работы с OpenAI API"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-5"):
        """
        Args:
            api_key: API ключ OpenAI
            model: Модель для использования
        """
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        
        # Папки для отладочных файлов
        project_root = Path(__file__).parent.parent.parent.parent
        self.debug_folder = project_root / 'storage' / 'debug'
        self.debug_folder.mkdir(parents=True, exist_ok=True)
        
        self.debug_prompts_folder = self.debug_folder / 'prompts'
        self.debug_responses_folder = self.debug_folder / 'responses'
        self.debug_prompts_folder.mkdir(exist_ok=True)
        self.debug_responses_folder.mkdir(exist_ok=True)
        
        # Инициализируем базовый класс
        super().__init__(api_key)
    
    def _load_api_key(self) -> Optional[str]:
        """Загружает API ключ из конфигурации"""
        project_root = Path(__file__).parent.parent.parent.parent
        api_key_file = project_root / 'key.txt'
        
        if api_key_file.exists():
            try:
                with open(api_key_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                pass
        
        return os.getenv('OPENAI_API_KEY')
    
    def get_model_name(self) -> str:
        """Возвращает название модели"""
        return self.model
    
    def process_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Обрабатывает промпт через OpenAI API
        
        Returns:
            {
                'success': bool,
                'json': dict,
                'usage': dict,
                'error': str
            }
        """
        # Импортируем здесь, чтобы не требовать при инициализации
        try:
            import openai
        except ImportError:
            return {
                'success': False,
                'json': None,
                'usage': None,
                'error': 'Библиотека openai не установлена. Установите: pip install openai'
            }
        
        try:
            client = openai.OpenAI(api_key=self.api_key)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Сохраняем промпт для отладки
            self._save_debug_prompt(prompt, timestamp)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты эксперт по технической документации. Твоя задача - заполнить JSON шаблон данными из технического задания. Отвечай только валидным JSON без дополнительных комментариев."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            content = response.choices[0].message.content if response.choices else None
            
            if not content or not content.strip():
                return {
                    'success': False,
                    'json': None,
                    'usage': None,
                    'error': 'Модель вернула пустой ответ'
                }
            
            # Извлекаем JSON
            json_data = self.extract_json(content)
            
            if json_data:
                return {
                    'success': True,
                    'json': json_data,
                    'usage': {
                        'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                        'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                        'total_tokens': response.usage.total_tokens if response.usage else 0
                    },
                    'error': None
                }
            else:
                self._save_debug_response(content, prompt, timestamp)
                return {
                    'success': False,
                    'json': None,
                    'usage': None,
                    'error': 'Не удалось извлечь валидный JSON из ответа ИИ'
                }
        
        except Exception as e:
            return {
                'success': False,
                'json': None,
                'usage': None,
                'error': f'Ошибка OpenAI API: {str(e)}'
            }
    
    def extract_json(self, text: str) -> Optional[dict]:
        """Извлекает JSON из текста"""
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'(\{.*\})',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                try:
                    return json.loads(matches[0])
                except json.JSONDecodeError:
                    continue
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    def _save_debug_prompt(self, prompt: str, timestamp: str):
        """Сохраняет промпт для отладки"""
        prompt_file = self.debug_prompts_folder / f"prompt_{timestamp}.txt"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(f"Модель: {self.model}\n")
            f.write("=" * 80 + "\n")
            f.write(prompt)
    
    def _save_debug_response(self, content: str, prompt: str, timestamp: str):
        """Сохраняет ответ для отладки"""
        response_file = self.debug_responses_folder / f"response_{timestamp}.txt"
        with open(response_file, 'w', encoding='utf-8') as f:
            f.write(f"Модель: {self.model}\n")
            f.write("=" * 80 + "\n")
            f.write(content)
        return str(response_file)
