#!/usr/bin/env python3
"""
Базовый класс для конвертеров документов
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseConverter(ABC):
    """Базовый класс для всех конвертеров документов"""
    
    @abstractmethod
    def convert(self, input_path: str, output_path: str) -> str:
        """
        Конвертирует документ в текстовый формат
        
        Args:
            input_path: Путь к исходному файлу
            output_path: Путь к выходному текстовому файлу
            
        Returns:
            Путь к созданному файлу
            
        Raises:
            DocumentConversionError: При ошибке конвертации
        """
        pass
    
    @abstractmethod
    def detect_format(self, file_path: str) -> Optional[str]:
        """
        Определяет формат файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Название формата или None
        """
        pass
    
    def validate_file(self, file_path: str) -> bool:
        """Проверяет существование файла"""
        return Path(file_path).exists()

