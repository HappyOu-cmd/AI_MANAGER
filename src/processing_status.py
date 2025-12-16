#!/usr/bin/env python3
"""
Модуль для отслеживания статуса обработки в реальном времени
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import threading


class ProcessingStatus:
    """Управление статусом обработки для отображения прогресса"""
    
    def __init__(self, status_dir: str = "storage/status"):
        """Инициализация менеджера статусов"""
        project_root = Path(__file__).parent.parent
        self.status_dir = project_root / status_dir
        self.status_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
    
    def create_status(self, task_id: str) -> Dict:
        """Создает новый статус обработки"""
        status = {
            'task_id': task_id,
            'status': 'pending',
            'stage': 'initialization',
            'progress': 0,
            'total_steps': 0,
            'current_step': 0,
            'message': 'Инициализация...',
            'metrics': {
                'start_time': datetime.now().isoformat(),
                'prompt_size': 0,
                'tokens_used': 0,
                'time_elapsed': 0
            },
            'errors': []
        }
        
        with self._lock:
            status_file = self.status_dir / f"{task_id}.json"
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        
        return status
    
    def update_status(self, task_id: str, **kwargs):
        """Обновляет статус обработки"""
        with self._lock:
            status_file = self.status_dir / f"{task_id}.json"
            
            if not status_file.exists():
                return
            
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status = json.load(f)
                
                # Обновляем поля
                status.update(kwargs)
                
                # Обновляем метрики времени
                if 'metrics' in status and 'start_time' in status['metrics']:
                    start_time = datetime.fromisoformat(status['metrics']['start_time'])
                    status['metrics']['time_elapsed'] = (datetime.now() - start_time).total_seconds()
                
                # Сохраняем
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(status, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"⚠️  Ошибка обновления статуса: {e}")
    
    def get_status(self, task_id: str) -> Optional[Dict]:
        """Получает текущий статус обработки (thread-safe чтение)"""
        status_file = self.status_dir / f"{task_id}.json"
        
        if not status_file.exists():
            return None
        
        try:
            # Чтение не требует блокировки, так как каждый task_id уникален
            with open(status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Ошибка чтения статуса: {e}")
            return None
    
    def delete_status(self, task_id: str):
        """Удаляет статус после завершения"""
        status_file = self.status_dir / f"{task_id}.json"
        if status_file.exists():
            try:
                status_file.unlink()
            except Exception as e:
                print(f"⚠️  Ошибка удаления статуса: {e}")
    
    def add_error(self, task_id: str, error: str):
        """Добавляет ошибку в статус"""
        status = self.get_status(task_id)
        if status:
            if 'errors' not in status:
                status['errors'] = []
            status['errors'].append(error)
            self.update_status(task_id, errors=status['errors'])
    
    def cancel_task(self, task_id: str) -> bool:
        """Отменяет задачу (устанавливает флаг cancelled)"""
        with self._lock:
            status_file = self.status_dir / f"{task_id}.json"
            
            if not status_file.exists():
                return False
            
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status = json.load(f)
                
                # Устанавливаем статус cancelled
                status['status'] = 'cancelled'
                status['message'] = 'Обработка отменена пользователем'
                
                # Сохраняем
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(status, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                print(f"⚠️  Ошибка отмены задачи: {e}")
                return False
    
    def is_cancelled(self, task_id: str) -> bool:
        """Проверяет, отменена ли задача"""
        status = self.get_status(task_id)
        if status:
            return status.get('status') == 'cancelled'
        return False

