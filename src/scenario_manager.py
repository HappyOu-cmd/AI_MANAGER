#!/usr/bin/env python3
"""
Модуль для управления сценариями обработки ТЗ
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class ScenarioManager:
    """Управление сценариями обработки ТЗ"""
    
    def __init__(self, scenarios_dir: str = "data/scenarios"):
        """Инициализация менеджера сценариев"""
        project_root = Path(__file__).parent.parent
        self.scenarios_dir = project_root / scenarios_dir
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
    
    def list_scenarios(self) -> List[Dict]:
        """Получить список всех сценариев"""
        scenarios = []
        
        if not self.scenarios_dir.exists():
            return scenarios
        
        for scenario_file in self.scenarios_dir.glob("*.json"):
            try:
                with open(scenario_file, 'r', encoding='utf-8') as f:
                    scenario = json.load(f)
                    scenarios.append(scenario)
            except Exception as e:
                print(f"⚠️  Ошибка чтения сценария {scenario_file}: {e}")
        
        # Сортируем по имени
        scenarios.sort(key=lambda x: x.get('name', ''))
        return scenarios
    
    def get_scenario(self, scenario_id: str) -> Optional[Dict]:
        """Получить сценарий по ID"""
        scenario_file = self.scenarios_dir / f"{scenario_id}.json"
        
        if not scenario_file.exists():
            return None
        
        try:
            with open(scenario_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Ошибка чтения сценария {scenario_file}: {e}")
            return None
    
    def create_scenario(self, scenario_data: Dict) -> Dict:
        """Создать новый сценарий"""
        # Генерируем ID если не указан
        if 'id' not in scenario_data or not scenario_data['id']:
            scenario_data['id'] = self._generate_id(scenario_data.get('name', 'scenario'))
        
        # Добавляем метаданные
        now = datetime.now().isoformat()
        scenario_data['created_at'] = scenario_data.get('created_at', now)
        scenario_data['updated_at'] = now
        
        # Валидация
        self._validate_scenario(scenario_data)
        
        # Сохраняем
        scenario_file = self.scenarios_dir / f"{scenario_data['id']}.json"
        with open(scenario_file, 'w', encoding='utf-8') as f:
            json.dump(scenario_data, f, ensure_ascii=False, indent=2)
        
        return scenario_data
    
    def update_scenario(self, scenario_id: str, scenario_data: Dict) -> Optional[Dict]:
        """Обновить существующий сценарий"""
        scenario_file = self.scenarios_dir / f"{scenario_id}.json"
        
        if not scenario_file.exists():
            return None
        
        # Загружаем существующий
        existing = self.get_scenario(scenario_id)
        if not existing:
            return None
        
        # Обновляем поля
        existing.update(scenario_data)
        existing['id'] = scenario_id  # Не позволяем менять ID
        existing['updated_at'] = datetime.now().isoformat()
        
        # Валидация
        self._validate_scenario(existing)
        
        # Сохраняем
        with open(scenario_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        
        return existing
    
    def delete_scenario(self, scenario_id: str) -> bool:
        """Удалить сценарий"""
        scenario_file = self.scenarios_dir / f"{scenario_id}.json"
        
        if not scenario_file.exists():
            return False
        
        try:
            scenario_file.unlink()
            return True
        except Exception as e:
            print(f"⚠️  Ошибка удаления сценария {scenario_file}: {e}")
            return False
    
    def list_available_prompts(self, machine_type: str = None) -> Dict[str, List[str]]:
        """Получить список доступных промптов"""
        project_root = Path(__file__).parent.parent
        prompts_dir = project_root / "data" / "prompts"
        
        result = {
            "main": [],
            "instrument": [],
            "tooling": [],
            "services": [],
            "spare_parts": []
        }
        
        if not prompts_dir.exists():
            return result
        
        # Если указан тип станка, ищем только в его папке
        if machine_type:
            machine_dir = prompts_dir / machine_type
            if machine_dir.exists():
                self._scan_prompts_in_dir(machine_dir, machine_type, result)
        else:
            # Сканируем все папки
            for machine_dir in prompts_dir.iterdir():
                if machine_dir.is_dir():
                    self._scan_prompts_in_dir(machine_dir, machine_dir.name, result)
        
        return result
    
    def list_available_templates(self) -> List[str]:
        """Получить список доступных TZ.json шаблонов"""
        project_root = Path(__file__).parent.parent
        data_dir = project_root / "data"
        
        templates = []
        
        # Ищем все TZ*.json файлы
        for tz_file in data_dir.glob("TZ*.json"):
            templates.append(str(tz_file.relative_to(project_root)))
        
        # Если нет специфичных, добавляем базовый
        if not templates and (data_dir / "TZ.json").exists():
            templates.append("data/TZ.json")
        
        return templates
    
    def list_available_glossaries(self) -> List[str]:
        """Получить список доступных glossary.json файлов"""
        project_root = Path(__file__).parent.parent
        data_dir = project_root / "data"
        
        glossaries = []
        
        # Ищем все glossary*.json файлы
        for gloss_file in data_dir.glob("glossary*.json"):
            glossaries.append(str(gloss_file.relative_to(project_root)))
        
        # Если нет специфичных, добавляем базовый
        if not glossaries and (data_dir / "glossary.json").exists():
            glossaries.append("data/glossary.json")
        
        return glossaries
    
    def _scan_prompts_in_dir(self, machine_dir: Path, machine_type: str, result: Dict):
        """Сканировать промпты в директории"""
        prompt_files = {
            "основной.txt": "main",
            "инструмент.txt": "instrument",
            "оснастка.txt": "tooling",
            "услуги.txt": "services",
            "зип.txt": "spare_parts"
        }
        
        for prompt_file in machine_dir.glob("*.txt"):
            filename = prompt_file.name
            if filename in prompt_files:
                prompt_type = prompt_files[filename]
                relative_path = f"data/prompts/{machine_type}/{filename}"
                result[prompt_type].append(relative_path)
    
    def _generate_id(self, name: str) -> str:
        """Генерировать ID из имени"""
        # Транслитерация и нормализация
        import re
        # Простая транслитерация кириллицы
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        
        name_lower = name.lower()
        id_parts = []
        for char in name_lower:
            if char in translit_map:
                id_parts.append(translit_map[char])
            elif char.isalnum():
                id_parts.append(char)
            elif char in ' -_':
                id_parts.append('_')
        
        base_id = ''.join(id_parts)
        base_id = re.sub(r'_+', '_', base_id)  # Убираем множественные подчеркивания
        base_id = base_id.strip('_')
        
        # Проверяем уникальность
        counter = 1
        scenario_id = base_id
        while (self.scenarios_dir / f"{scenario_id}.json").exists():
            scenario_id = f"{base_id}_{counter}"
            counter += 1
        
        return scenario_id
    
    def _validate_scenario(self, scenario: Dict):
        """Валидация структуры сценария"""
        required_fields = ['id', 'name', 'machine_type', 'prompts']
        
        for field in required_fields:
            if field not in scenario:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
        
        # Валидация промптов
        prompts = scenario['prompts']
        required_prompt_types = ['main', 'instrument', 'tooling', 'services', 'spare_parts']
        
        for prompt_type in required_prompt_types:
            if prompt_type not in prompts:
                raise ValueError(f"Отсутствует тип промпта: {prompt_type}")
            
            prompt_config = prompts[prompt_type]
            if not isinstance(prompt_config, dict):
                raise ValueError(f"Неверный формат конфигурации промпта: {prompt_type}")
            
            if 'enabled' not in prompt_config:
                raise ValueError(f"Отсутствует поле 'enabled' для промпта: {prompt_type}")
            
            # Для main промпта проверяем наличие файлов TZ и glossary
            if prompt_type == 'main' and prompt_config.get('enabled'):
                if 'tz_template' not in prompt_config:
                    raise ValueError("Отсутствует поле 'tz_template' для основного промпта")
                if 'glossary' not in prompt_config:
                    raise ValueError("Отсутствует поле 'glossary' для основного промпта")
                
                # Проверяем существование файлов
                project_root = Path(__file__).parent.parent
                tz_path = project_root / prompt_config['tz_template']
                gloss_path = project_root / prompt_config['glossary']
                
                if not tz_path.exists():
                    raise ValueError(f"Файл TZ не найден: {tz_path}")
                if not gloss_path.exists():
                    raise ValueError(f"Файл glossary не найден: {gloss_path}")
            
            # Проверяем существование файла промпта если он включен
            if prompt_config.get('enabled') and 'file' in prompt_config:
                project_root = Path(__file__).parent.parent
                prompt_path = project_root / prompt_config['file']
                if not prompt_path.exists():
                    raise ValueError(f"Файл промпта не найден: {prompt_path}")

