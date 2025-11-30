#!/usr/bin/env python3
"""
Модуль для построения промпта с подстановкой значений
"""

import json
from pathlib import Path
from typing import Optional


class PromptBuilder:
    """Строит промпт для ИИ с подстановкой шаблона JSON, глоссария и текста ТЗ"""
    
    def __init__(self, prompt_file: str = "Промпт.txt", tz_template_file: str = "TZ.json", glossary_file: str = "glossary.json"):
        # Определяем корень проекта (на уровень выше src/)
        project_root = Path(__file__).parent.parent
        self.prompt_file = project_root / prompt_file
        self.tz_template_file = project_root / tz_template_file
        self.glossary_file = project_root / glossary_file
        self.prompt_template = None
        
    def load_prompt_template(self) -> str:
        """Загружает шаблон промпта из файла"""
        if not self.prompt_file.exists():
            raise FileNotFoundError(
                f"Файл промпта не найден: {self.prompt_file}\n"
                f"Текущая рабочая директория: {Path.cwd()}\n"
                f"Корень проекта: {self.prompt_file.parent}"
            )
        
        try:
            with open(self.prompt_file, 'r', encoding='utf-8') as f:
                self.prompt_template = f.read()
            
            if not self.prompt_template.strip():
                raise ValueError(f"Файл промпта пустой: {self.prompt_file}")
            
            return self.prompt_template
        except IOError as e:
            raise IOError(
                f"Ошибка чтения файла промпта: {str(e)}\n"
                f"Файл: {self.prompt_file}"
            )
    
    def load_tz_template(self) -> dict:
        """Загружает шаблон TZ.json"""
        if not self.tz_template_file.exists():
            raise FileNotFoundError(
                f"Файл TZ.json не найден: {self.tz_template_file}\n"
                f"Текущая рабочая директория: {Path.cwd()}\n"
                f"Корень проекта: {self.tz_template_file.parent}"
            )
        
        try:
            with open(self.tz_template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Убираем пробелы и переносы строк только с краев
            content_stripped = content.strip()
            
            if not content_stripped:
                file_size = self.tz_template_file.stat().st_size
                raise ValueError(
                    f"Файл TZ.json пустой или содержит только пробелы: {self.tz_template_file}\n"
                    f"Размер файла: {file_size} байт"
                )
            
            # Пытаемся распарсить JSON
            try:
                return json.loads(content_stripped)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Ошибка парсинга JSON в файле TZ.json: {str(e)}\n"
                    f"Файл: {self.tz_template_file}\n"
                    f"Первые 200 символов: {content_stripped[:200]}"
                )
        except IOError as e:
            raise IOError(
                f"Ошибка чтения файла TZ.json: {str(e)}\n"
                f"Файл: {self.tz_template_file}"
            )
    
    def load_glossary(self) -> dict:
        """Загружает глоссарий glossary.json"""
        if not self.glossary_file.exists():
            raise FileNotFoundError(
                f"Файл glossary.json не найден: {self.glossary_file}\n"
                f"Текущая рабочая директория: {Path.cwd()}\n"
                f"Корень проекта: {self.glossary_file.parent}\n"
                f"Создайте файл glossary.json, запустив конвертер Excel → JSON"
            )
        
        try:
            with open(self.glossary_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Убираем пробелы и переносы строк только с краев
            content_stripped = content.strip()
            
            if not content_stripped:
                file_size = self.glossary_file.stat().st_size
                raise ValueError(
                    f"Файл glossary.json пустой или содержит только пробелы: {self.glossary_file}\n"
                    f"Размер файла: {file_size} байт"
                )
            
            # Пытаемся распарсить JSON
            try:
                return json.loads(content_stripped)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Ошибка парсинга JSON в файле glossary.json: {str(e)}\n"
                    f"Файл: {self.glossary_file}\n"
                    f"Первые 200 символов: {content_stripped[:200]}"
                )
        except IOError as e:
            raise IOError(
                f"Ошибка чтения файла glossary.json: {str(e)}\n"
                f"Файл: {self.glossary_file}"
            )
    
    def build_prompt(self, converted_text: str, tz_json: Optional[dict] = None, glossary: Optional[dict] = None) -> str:
        """
        Строит финальный промпт с подстановкой значений
        
        Args:
            converted_text: Текст из сконвертированного документа
            tz_json: JSON шаблон (если None, загружается из файла)
            glossary: JSON глоссарий (если None, загружается из файла)
        
        Returns:
            Готовый промпт для отправки в ИИ
        """
        if self.prompt_template is None:
            self.load_prompt_template()
        
        if tz_json is None:
            tz_json = self.load_tz_template()
        
        if glossary is None:
            glossary = self.load_glossary()
        
        # Форматируем JSON для вставки в промпт
        tz_json_str = json.dumps(tz_json, ensure_ascii=False, indent=2)
        glossary_json_str = json.dumps(glossary, ensure_ascii=False, indent=2)
        
        # Заменяем плейсхолдеры в промпте
        prompt = self.prompt_template
        
        # Заменяем плейсхолдеры в конце промпта (строки 98-102)
        # Формат в промпте:
        # JSON-шаблон параметров станка
        # 
        # JSON-глоссарий
        # 
        # Текст ТЗ
        # 
        # После каждого плейсхолдера вставляем соответствующие данные
        # Важно: заменяем только последние вхождения (в конце файла), а не первые (в описании)
        
        # 1. JSON-шаблон параметров станка -> вставляем TZ.json
        # Ищем последнее вхождение в конце файла
        pattern_tz = "JSON-шаблон параметров станка\n\n"
        if pattern_tz in prompt:
            # Находим последнее вхождение
            last_pos = prompt.rfind(pattern_tz)
            if last_pos >= 0:
                prompt = prompt[:last_pos] + f"JSON-шаблон параметров станка\n{tz_json_str}\n\n" + prompt[last_pos + len(pattern_tz):]
        
        # 2. JSON-глоссарий -> вставляем glossary.json
        # Ищем последнее вхождение в конце файла (не в описании в начале)
        pattern_glossary = "\nJSON-глоссарий\n\n"
        if pattern_glossary in prompt:
            # Находим последнее вхождение
            last_pos = prompt.rfind(pattern_glossary)
            if last_pos >= 0:
                prompt = prompt[:last_pos] + f"\nJSON-глоссарий\n{glossary_json_str}\n\n" + prompt[last_pos + len(pattern_glossary):]
        else:
            # Пробуем без переноса в начале
            pattern_glossary2 = "JSON-глоссарий\n\n"
            if pattern_glossary2 in prompt:
                last_pos = prompt.rfind(pattern_glossary2)
                if last_pos >= 0:
                    prompt = prompt[:last_pos] + f"JSON-глоссарий\n{glossary_json_str}\n\n" + prompt[last_pos + len(pattern_glossary2):]
        
        # 3. Текст ТЗ -> вставляем конвертированный текст
        # Ищем последнее вхождение в конце файла
        pattern_text = "\nТекст ТЗ\n"
        if pattern_text in prompt:
            last_pos = prompt.rfind(pattern_text)
            if last_pos >= 0:
                prompt = prompt[:last_pos] + f"\nТекст ТЗ\n{converted_text}\n" + prompt[last_pos + len(pattern_text):]
        elif prompt.endswith("Текст ТЗ\n"):
            prompt = prompt[:-len("Текст ТЗ\n")] + f"Текст ТЗ\n{converted_text}\n"
        
        # Также обрабатываем старые варианты плейсхолдеров (для обратной совместимости)
        prompt = prompt.replace(
            "Шаблон JSON:\n\n",
            f"JSON-шаблон параметров станка\n{tz_json_str}\n\n"
        )
        
        prompt = prompt.replace(
            "Текст ТЗ:\n\n",
            f"Текст ТЗ\n{converted_text}\n\n"
        )
        
        return prompt
    
    def save_prompt(self, prompt: str, output_file: str = "prompt_final.txt"):
        """Сохраняет финальный промпт в файл (для отладки)"""
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(prompt)
        return str(output_path)

