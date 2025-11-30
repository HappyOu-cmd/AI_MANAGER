#!/usr/bin/env python3
"""
Базовый класс для AI клиентов
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseAIClient(ABC):
    """Базовый класс для всех AI клиентов"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: API ключ (если None, загружается из конфигурации)
        """
        self.api_key = api_key or self._load_api_key()
        if not self.api_key:
            raise ValueError("API ключ не найден")
    
    @abstractmethod
    def _load_api_key(self) -> Optional[str]:
        """Загружает API ключ из конфигурации"""
        pass
    
    @abstractmethod
    def process_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Обрабатывает промпт и возвращает результат
        
        Args:
            prompt: Текст промпта
            
        Returns:
            Словарь с результатом:
            {
                'success': bool,
                'json': dict,  # Заполненный JSON
                'usage': dict,  # Информация об использовании токенов
                'error': str  # Сообщение об ошибке (если success=False)
            }
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Возвращает название используемой модели"""
        pass

