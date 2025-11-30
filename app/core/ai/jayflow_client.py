#!/usr/bin/env python3
"""
JayFlow API клиент
Наследуется от базового класса BaseAIClient
"""

import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from app.core.ai.base import BaseAIClient


class JayFlowClient(BaseAIClient):
    """Клиент для работы с Jay Flow API"""
    
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Args:
            api_url: URL API Jay Flow
            api_key: API ключ Jay Flow
        """
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Загружаем URL
        if api_url:
            self.api_url = api_url
        else:
            api_url_file = project_root / 'JayFlowClientHTTP.txt'
            if api_url_file.exists():
                with open(api_url_file, 'r', encoding='utf-8') as f:
                    self.api_url = f.read().strip()
            else:
                raise ValueError("URL Jay Flow API не найден. Создайте файл JayFlowClientHTTP.txt")
        
        # Настройки
        self.thread_id = None
        self.verify_ssl = os.getenv('JAYFLOW_VERIFY_SSL', 'true').lower() not in ('false', '0', 'no')
        
        # Отладочные папки
        self.debug_folder = project_root / 'storage' / 'debug'
        self.debug_folder.mkdir(parents=True, exist_ok=True)
        self.debug_prompts_folder = self.debug_folder / 'prompts'
        self.debug_responses_folder = self.debug_folder / 'responses'
        self.debug_prompts_folder.mkdir(exist_ok=True)
        self.debug_responses_folder.mkdir(exist_ok=True)
        
        # Инициализируем базовый класс
        super().__init__(api_key)
    
    def _load_api_key(self) -> Optional[str]:
        """Загружает API ключ"""
        project_root = Path(__file__).parent.parent.parent.parent
        api_key_file = project_root / 'key.txt'
        
        if api_key_file.exists():
            try:
                with open(api_key_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                pass
        
        return os.getenv('JAYFLOW_API_KEY')
    
    def get_model_name(self) -> str:
        """Возвращает название модели"""
        return "jayflow"
    
    def process_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Обрабатывает промпт через Jay Flow API
        
        Returns:
            {
                'success': bool,
                'json': dict,
                'usage': dict,
                'error': str
            }
        """
        try:
            import requests
        except ImportError:
            return {
                'success': False,
                'json': None,
                'usage': None,
                'error': 'Библиотека requests не установлена. Установите: pip install requests'
            }
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._save_debug_prompt(prompt, timestamp)
            
            # Используем POST для больших промптов
            use_post = len(prompt) > 1500
            
            headers = {}
            if self.api_key:
                headers['Authorization'] = self.api_key
            if use_post:
                headers['Content-Type'] = 'application/json'
            
            data = {'input': prompt}
            if self.thread_id:
                data['threadId'] = self.thread_id
            
            if use_post:
                response = requests.post(
                    self.api_url,
                    json=data,
                    headers=headers,
                    timeout=300,
                    verify=self.verify_ssl
                )
            else:
                response = requests.get(
                    self.api_url,
                    params=data,
                    headers=headers,
                    timeout=300,
                    verify=self.verify_ssl
                )
            
            response.raise_for_status()
            result = response.json()
            
            content = result.get('content', '')
            self.thread_id = result.get('threadId')
            
            # Извлекаем JSON
            json_data = self.extract_json(content)
            
            if json_data:
                return {
                    'success': True,
                    'json': json_data,
                    'usage': {},  # JayFlow не предоставляет информацию о токенах
                    'error': None
                }
            else:
                self._save_debug_response(content, prompt, timestamp)
                return {
                    'success': False,
                    'json': None,
                    'usage': None,
                    'error': 'Не удалось извлечь валидный JSON из ответа Jay Flow'
                }
        
        except Exception as e:
            return {
                'success': False,
                'json': None,
                'usage': None,
                'error': f'Ошибка Jay Flow API: {str(e)}'
            }
    
    def extract_json(self, text: str) -> Optional[dict]:
        """Извлекает JSON из текста"""
        import re
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
        prompt_file = self.debug_prompts_folder / f"prompt_jayflow_{timestamp}.txt"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write("Jay Flow API\n")
            f.write("=" * 80 + "\n")
            f.write(prompt)
    
    def _save_debug_response(self, content: str, prompt: str, timestamp: str):
        """Сохраняет ответ для отладки"""
        response_file = self.debug_responses_folder / f"response_jayflow_{timestamp}.txt"
        with open(response_file, 'w', encoding='utf-8') as f:
            f.write("Jay Flow API\n")
            f.write("=" * 80 + "\n")
            f.write(content)
        return str(response_file)
