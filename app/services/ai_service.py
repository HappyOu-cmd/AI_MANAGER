#!/usr/bin/env python3
"""
Сервис для работы с AI провайдерами
"""

from typing import Dict, Any

from app.core.ai.openai_client import OpenAIClient
from app.core.ai.jayflow_client import JayFlowClient
from app.utils.exceptions import AIProcessingError


class AIService:
    """Сервис для работы с различными AI провайдерами"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Конфигурация приложения
        """
        self.config = config
        self._clients = {}
    
    def _get_client(self, provider: str):
        """Получает клиент для указанного провайдера"""
        if provider in self._clients:
            return self._clients[provider]
        
        if provider == 'openai':
            client = OpenAIClient(
                api_key=self.config.get('OPENAI_API_KEY'),
                model=self.config.get('OPENAI_MODEL', 'gpt-5')
            )
        elif provider == 'jayflow':
            client = JayFlowClient()
        else:
            raise ValueError(f"Неподдерживаемый провайдер ИИ: {provider}")
        
        self._clients[provider] = client
        return client
    
    def process_with_ai(self, prompt: str, provider: str = 'openai') -> Dict[str, Any]:
        """
        Обрабатывает промпт через указанного провайдера ИИ
        
        Args:
            prompt: Текст промпта
            provider: Провайдер ИИ ('openai' или 'jayflow')
            
        Returns:
            Результат обработки
        """
        if provider not in self.config.get('SUPPORTED_AI_PROVIDERS', []):
            raise AIProcessingError(f"Неподдерживаемый провайдер: {provider}")
        
        try:
            client = self._get_client(provider)
            return client.process_prompt(prompt)
        except Exception as e:
            raise AIProcessingError(f"Ошибка обработки через {provider}: {str(e)}")

