#!/usr/bin/env python3
"""
Валидаторы для проверки данных
"""

from pathlib import Path
from typing import List
from werkzeug.utils import secure_filename


class FileValidator:
    """Валидатор для файлов"""
    
    def __init__(self, allowed_extensions: List[str], max_size: int):
        """
        Args:
            allowed_extensions: Список разрешенных расширений (без точки)
            max_size: Максимальный размер файла в байтах
        """
        self.allowed_extensions = {ext.lower().lstrip('.') for ext in allowed_extensions}
        self.max_size = max_size
    
    def is_allowed_extension(self, filename: str) -> bool:
        """Проверяет, разрешено ли расширение файла"""
        if '.' not in filename:
            return False
        
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in self.allowed_extensions
    
    def is_valid_size(self, file_size: int) -> bool:
        """Проверяет, не превышает ли файл максимальный размер"""
        return file_size <= self.max_size
    
    def validate_file(self, filename: str, file_size: int = None) -> tuple[bool, str]:
        """
        Валидирует файл
        
        Returns:
            (is_valid, error_message)
        """
        if not filename:
            return False, "Имя файла не может быть пустым"
        
        if not self.is_allowed_extension(filename):
            allowed = ', '.join(self.allowed_extensions)
            return False, f"Неподдерживаемый формат. Разрешены: {allowed}"
        
        if file_size and not self.is_valid_size(file_size):
            max_mb = self.max_size / (1024 * 1024)
            return False, f"Файл слишком большой. Максимальный размер: {max_mb} МБ"
        
        return True, ""
    
    def secure_filename(self, filename: str) -> str:
        """Безопасное имя файла"""
        return secure_filename(filename)

