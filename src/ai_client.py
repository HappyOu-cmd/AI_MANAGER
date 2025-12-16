#!/usr/bin/env python3
"""
Модуль для работы с OpenAI API
"""

import os
import json
import time
from typing import Optional, Dict, Any
import re
from pathlib import Path
from datetime import datetime
import logging

# Настраиваем логирование
logger = logging.getLogger(__name__)


class OpenAIClient:
    """Клиент для работы с OpenAI API"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-5"):
        """
        Инициализация клиента
        
        Args:
            api_key: API ключ OpenAI (если None, берется из файла key.txt или переменной окружения)
            model: Модель для использования (по умолчанию gpt-5)
                    Доступные модели: gpt-5, gpt-5-mini, gpt-5.1, gpt-4o, gpt-4-turbo, gpt-3.5-turbo, gpt-4o-mini
        """
        # Инициализируем модель сразу
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        
        # Папки для отладочных файлов
        project_root = Path(__file__).parent.parent
        self.debug_folder = project_root / 'debug'
        self.debug_folder.mkdir(exist_ok=True)
        
        # Отдельные папки для промптов и ответов
        self.debug_prompts_folder = self.debug_folder / 'prompts'
        self.debug_responses_folder = self.debug_folder / 'responses'
        self.debug_prompts_folder.mkdir(exist_ok=True)
        self.debug_responses_folder.mkdir(exist_ok=True)
        
        if api_key:
            self.api_key = api_key
        else:
            # Пытаемся прочитать из файла key.txt
            self.api_key = self._load_api_key_from_file()
            
            # Если не нашли в файле, пробуем переменную окружения
            if not self.api_key:
                self.api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "API ключ не найден.\n"
                "Создайте файл key.txt в корне проекта и поместите туда ваш API ключ,\n"
                "или установите переменную окружения OPENAI_API_KEY:\n"
                "  export OPENAI_API_KEY='your-api-key-here'"
            )
        
        # Убираем пробелы и переносы строк
        self.api_key = self.api_key.strip()
    
    def _load_api_key_from_file(self) -> Optional[str]:
        """
        Загружает API ключ из файла key.txt
        
        Returns:
            API ключ или None, если файл не найден или пуст
        """
        # Определяем корень проекта (на уровень выше src/)
        project_root = Path(__file__).parent.parent
        api_key_file = project_root / 'key.txt'
        
        if not api_key_file.exists():
            return None
        
        try:
            with open(api_key_file, 'r', encoding='utf-8') as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception as e:
            # В случае ошибки чтения файла возвращаем None
            print(f"⚠️  Ошибка чтения key.txt: {e}")
            return None
        
        return None
    
    def _make_request(self, prompt: str, save_prompt: bool = True, timestamp: str = None) -> Dict[str, Any]:
        """
        Отправляет запрос в OpenAI API
        
        Args:
            prompt: Текст промпта
            save_prompt: Сохранять ли промпт для отладки
            timestamp: Временная метка для связанных файлов
        
        Returns:
            Ответ от API
        """
        try:
            import openai
        except ImportError:
            raise ImportError(
                "Библиотека openai не установлена. Установите:\n"
                "  pip install openai"
            )
        
        # Настройка клиента
        client = openai.OpenAI(api_key=self.api_key)
        
        # Сохраняем промпт для отладки (если нужно)
        if save_prompt:
            if timestamp is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._save_debug_prompt(prompt, timestamp)
        elif timestamp is None:
            # Если не сохраняем промпт, все равно нужна временная метка для ответа
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Проверяем размер промпта перед отправкой
        prompt_size = len(prompt)
        estimated_tokens = prompt_size // 4  # Примерная оценка (1 токен ≈ 4 символа)
        
        # Предупреждение о большом промпте
        if estimated_tokens > 100000:
            print(f"⚠️  Внимание: Очень большой промпт (~{estimated_tokens:,} токенов). Это может вызвать ошибки.")
        
        try:
            logger.info(f"🚀 Отправка запроса в OpenAI API (модель: {self.model}, промпт: {prompt_size:,} символов)")
            start_time = time.time()
            
            # Минимальный запрос - только model и messages
            # Не ограничиваем контекст и не передаем лишние параметры
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
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ Получен ответ от OpenAI API за {elapsed_time:.2f} секунд")
            
            # Извлекаем контент из ответа
            content = response.choices[0].message.content if response.choices else None
            finish_reason = response.choices[0].finish_reason if response.choices else None
            
            # Логируем информацию об использовании токенов
            if response.usage:
                logger.info(f"📊 Использовано токенов: {response.usage.total_tokens:,} "
                          f"(промпт: {response.usage.prompt_tokens:,}, "
                          f"ответ: {response.usage.completion_tokens:,})")
            
            if content:
                logger.info(f"📥 Размер ответа: {len(content):,} символов")
            else:
                logger.warning(f"⚠️  Пустой ответ от API (finish_reason: {finish_reason})")
            
            # Проверяем, что контент не пустой
            if not content or not content.strip():
                # Проверяем, не был ли ответ обрезан из-за лимита токенов
                if finish_reason == 'length':
                    debug_info = {
                        'model': self.model,
                        'finish_reason': finish_reason,
                        'response_structure': str(response),
                        'choices_count': len(response.choices) if response.choices else 0,
                        'usage': {
                            'prompt_tokens': response.usage.prompt_tokens if response.usage else None,
                            'completion_tokens': response.usage.completion_tokens if response.usage else None,
                            'total_tokens': response.usage.total_tokens if response.usage else None,
                            'reasoning_tokens': getattr(response.usage.completion_tokens_details, 'reasoning_tokens', None) if response.usage and hasattr(response.usage, 'completion_tokens_details') else None
                        }
                    }
                    debug_file = self._save_debug_response("", prompt, timestamp)
                    with open(debug_file, 'a', encoding='utf-8') as f:
                        f.write("\n" + "=" * 80 + "\n")
                        f.write("СТРУКТУРА ОТВЕТА API:\n")
                        f.write("=" * 80 + "\n")
                        f.write(json.dumps(debug_info, ensure_ascii=False, indent=2))
                    
                    return {
                        'success': False,
                        'error': (
                            'Ответ был обрезан из-за лимита токенов (finish_reason=length).\n\n'
                            f'Использовано токенов: {response.usage.completion_tokens if response.usage else 0}\n'
                            f'Reasoning tokens: {getattr(response.usage.completion_tokens_details, "reasoning_tokens", 0) if response.usage and hasattr(response.usage, "completion_tokens_details") else "N/A"}\n\n'
                            'Модель gpt-5-nano использует reasoning tokens, которые занимают место в лимите.\n'
                            'Попробуйте:\n'
                            '1. Уменьшить размер промпта\n'
                            '2. Использовать другую модель (gpt-4o, gpt-4o-mini)\n'
                            '3. Увеличить max_completion_tokens\n\n'
                            f'📁 Полная информация сохранена: {debug_file}'
                        ),
                        'error_type': 'length_limit'
                    }
                # Сохраняем полный ответ для отладки
                debug_info = {
                    'model': self.model,
                    'response_structure': str(response),
                    'choices_count': len(response.choices) if response.choices else 0,
                    'first_choice': str(response.choices[0]) if response.choices else None,
                    'usage': {
                        'prompt_tokens': response.usage.prompt_tokens if response.usage else None,
                        'completion_tokens': response.usage.completion_tokens if response.usage else None,
                        'total_tokens': response.usage.total_tokens if response.usage else None
                    }
                }
                debug_file = self._save_debug_response("", prompt, timestamp)
                # Дополняем файл информацией о структуре ответа
                with open(debug_file, 'a', encoding='utf-8') as f:
                    f.write("\n" + "=" * 80 + "\n")
                    f.write("СТРУКТУРА ОТВЕТА API:\n")
                    f.write("=" * 80 + "\n")
                    f.write(json.dumps(debug_info, ensure_ascii=False, indent=2))
                
                return {
                    'success': False,
                    'error': (
                        'Модель вернула пустой ответ.\n\n'
                        'Возможные причины:\n'
                        '1. Модель не поддерживает такой тип запросов\n'
                        '2. Промпт слишком сложный для этой модели\n'
                        '3. Проблема с параметрами запроса\n\n'
                        f'📁 Полная информация сохранена: {debug_file}'
                    ),
                    'error_type': 'empty_response'
                }
            
            return {
                'success': True,
                'content': content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                    'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                    'total_tokens': response.usage.total_tokens if response.usage else 0
                }
            }
        
        except openai.AuthenticationError as e:
            return {
                'success': False,
                'error': (
                    '❌ Неверный API ключ!\n\n'
                    'Проверьте файл key.txt в корне проекта:\n'
                    '1. Убедитесь, что ключ скопирован полностью\n'
                    '2. Проверьте, что ключ не истек\n'
                    '3. Получите новый ключ: https://platform.openai.com/account/api-keys\n\n'
                    f'Техническая информация: {str(e)}'
                ),
                'error_type': 'authentication_error'
            }
        
        except openai.RateLimitError as e:
            error_str = str(e)
            
            # Проверяем, является ли это ошибкой лимита токенов
            if 'tokens per min' in error_str or 'TPM' in error_str or 'tokens' in error_str.lower():
                # Извлекаем информацию о лимите и запросе
                limit_match = None
                requested_match = None
                
                if 'Limit' in error_str and 'Requested' in error_str:
                    import re
                    limit_match = re.search(r'Limit (\d+)', error_str)
                    requested_match = re.search(r'Requested (\d+)', error_str)
                
                limit = limit_match.group(1) if limit_match else "N/A"
                requested = requested_match.group(1) if requested_match else "N/A"
                
                return {
                    'success': False,
                    'error': (
                        '❌ Превышен лимит токенов в минуту (TPM)!\n\n'
                        f'Лимит модели {self.model}: {limit} токенов/мин\n'
                        f'Запрошено: {requested} токенов\n\n'
                        '⚠️  Важно: Окно контекста (250K) ≠ Лимит скорости (TPM)\n'
                        '• Окно контекста: максимальный размер одного запроса (250K) ✅\n'
                        '• TPM: лимит скорости - сколько токенов можно отправить в минуту (30K) ❌\n\n'
                        'Решения:\n'
                        '1. Увеличьте лимит TPM в настройках организации:\n'
                        '   https://platform.openai.com/settings/organization/limits\n'
                        '   (для корпоративных аккаунтов доступны лимиты до 3M-10M TPM)\n\n'
                        '2. Используйте модель с большим лимитом TPM:\n'
                        '   • gpt-4o (обычно имеет больший лимит TPM)\n'
                        '   • gpt-4o-mini (быстрая и дешевая)\n\n'
                        '3. Уменьшите размер промпта (~{:.0f} токенов сейчас):\n'
                        '   • Сократите входной документ\n'
                        '   • Удалите лишние части из ТЗ\n\n'
                        '4. Подождите минуту - лимит TPM сбрасывается каждую минуту\n\n'
                        'Чтобы изменить модель, отредактируйте:\n'
                        'src/ai_client.py (строка 18)\n\n'
                        f'Техническая информация: {error_str[:300]}'
                    ).format(int(requested) if requested != "N/A" else 0),
                    'error_type': 'token_limit'
                }
            
            return {
                'success': False,
                'error': f'Превышен лимит запросов. Попробуйте позже. {str(e)}',
                'error_type': 'rate_limit'
            }
        
        except openai.APIError as e:
            error_str = str(e)
            error_code = getattr(e, 'status_code', None) or (str(e).split('code: ')[1].split(',')[0] if 'code: ' in str(e) else None)
            
            # Обработка ошибки 500 (внутренняя ошибка сервера)
            if error_code == 500 or '500' in error_str or 'server_error' in error_str:
                # Сохраняем информацию о промпте для отладки
                prompt_size = len(prompt)
                estimated_tokens = prompt_size // 4  # Примерная оценка
                
                return {
                    'success': False,
                    'error': (
                        '❌ Внутренняя ошибка сервера OpenAI (500).\n\n'
                        f'Размер промпта: {prompt_size:,} символов (~{estimated_tokens:,} токенов)\n\n'
                        'Возможные причины:\n'
                        '1. Промпт слишком большой для модели\n'
                        '2. Временные проблемы на сервере OpenAI\n'
                        '3. Модель может не поддерживать такие большие промпты\n\n'
                        'Рекомендации:\n'
                        '• Попробуйте использовать другую модель (gpt-4o, gpt-4o-mini)\n'
                        '• Уменьшите размер входного документа\n'
                        '• Разбейте задачу на несколько запросов\n'
                        '• Попробуйте повторить запрос через несколько секунд\n\n'
                        f'Техническая информация: {error_str[:300]}'
                    ),
                    'error_type': 'server_error'
                }
            
            # Проверяем, является ли это ошибкой неверного ключа
            if '401' in error_str or 'invalid_api_key' in error_str or 'Incorrect API key' in error_str:
                return {
                    'success': False,
                    'error': (
                        '❌ Неверный или истекший API ключ!\n\n'
                        'Что делать:\n'
                        '1. Откройте файл key.txt в корне проекта\n'
                        '2. Получите новый API ключ: https://platform.openai.com/account/api-keys\n'
                        '3. Замените старый ключ на новый (без пробелов и переносов строк)\n'
                        '4. Сохраните файл и перезапустите сервер\n\n'
                        f'Техническая информация: {error_str[:200]}'
                    ),
                    'error_type': 'authentication_error'
                }
            # Проверяем, является ли это ошибкой несуществующей модели
            if '404' in error_str or 'model_not_found' in error_str or 'does not exist' in error_str:
                return {
                    'success': False,
                    'error': (
                        '❌ Модель не найдена или недоступна!\n\n'
                        f'Запрошенная модель: {self.model}\n\n'
                        'Доступные модели:\n'
                        '• gpt-4o (рекомендуется)\n'
                        '• gpt-4-turbo\n'
                        '• gpt-4o-mini (быстрая и дешевая)\n'
                        '• gpt-3.5-turbo\n\n'
                        'Чтобы изменить модель, отредактируйте файл:\n'
                        'src/ai_client.py (строка 17)\n\n'
                        f'Техническая информация: {error_str[:200]}'
                    ),
                    'error_type': 'model_not_found'
                }
            return {
                'success': False,
                'error': f'Ошибка API: {error_str}',
                'error_type': 'api_error'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Неожиданная ошибка: {str(e)}',
                'error_type': 'unknown'
            }
    
    def _save_debug_prompt(self, prompt: str, timestamp: str = None) -> str:
        """
        Сохраняет промпт в файл для отладки
        
        Args:
            prompt: Промпт для отправки в ИИ
            timestamp: Временная метка (если None, генерируется автоматически)
        
        Returns:
            Путь к сохраненному файлу
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        prompt_file = self.debug_prompts_folder / f"prompt_{timestamp}.txt"
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"ОТЛАДОЧНЫЙ ФАЙЛ - Промпт для ИИ\n")
            f.write(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Модель: {self.model}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("ПРОМПТ:\n")
            f.write("-" * 80 + "\n")
            f.write(prompt)
            f.write("\n" + "-" * 80 + "\n\n")
            
            f.write("ИНФОРМАЦИЯ:\n")
            f.write(f"Длина промпта: {len(prompt)} символов\n")
            # Примерная оценка токенов (1 токен ≈ 4 символа)
            estimated_tokens = len(prompt) // 4
            f.write(f"Примерное количество токенов: ~{estimated_tokens}\n")
            f.write(f"Первые 500 символов: {prompt[:500]}\n")
            f.write(f"Последние 500 символов: {prompt[-500:]}\n")
        
        return str(prompt_file)
    
    def _save_debug_response(self, content: str, prompt: str = None, timestamp: str = None) -> str:
        """
        Сохраняет ответ ИИ в файл для отладки
        
        Args:
            content: Содержимое ответа от ИИ
            prompt: Промпт (опционально, для ссылки на файл промпта)
            timestamp: Временная метка (если None, генерируется автоматически)
        
        Returns:
            Путь к сохраненному файлу
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        response_file = self.debug_responses_folder / f"response_{timestamp}.txt"
        
        with open(response_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"ОТЛАДОЧНЫЙ ФАЙЛ - Ответ ИИ\n")
            f.write(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Модель: {self.model}\n")
            if prompt:
                prompt_file = self.debug_prompts_folder / f"prompt_{timestamp}.txt"
                f.write(f"Связанный промпт: {prompt_file}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("ОТВЕТ ИИ:\n")
            f.write("-" * 80 + "\n")
            f.write(content if content else "(пустой ответ)")
            f.write("\n" + "-" * 80 + "\n\n")
            
            f.write("ИНФОРМАЦИЯ:\n")
            f.write(f"Длина ответа: {len(content)} символов\n")
            if content:
                f.write(f"Первые 200 символов: {content[:200]}\n")
                f.write(f"Последние 200 символов: {content[-200:]}\n")
            else:
                f.write("Ответ пустой!\n")
        
        return str(response_file)
    
    def extract_json(self, text: str) -> Optional[dict]:
        """
        Извлекает JSON из текста ответа
        
        Args:
            text: Текст ответа от ИИ
        
        Returns:
            Распарсенный JSON или None
        """
        # Пытаемся найти JSON в тексте
        # Ищем блоки между ```json и ``` или просто валидный JSON
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',  # JSON в блоке кода
            r'```\s*(\{.*?\})\s*```',      # JSON в блоке без указания языка
            r'(\{.*\})',                    # Просто JSON объект
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                try:
                    return json.loads(matches[0])
                except json.JSONDecodeError:
                    continue
        
        # Если ничего не найдено, пытаемся распарсить весь текст
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    def process_prompt(self, prompt: str, max_retries: int = 2) -> Dict[str, Any]:
        """
        Обрабатывает промпт и возвращает заполненный JSON
        
        Args:
            prompt: Промпт для отправки
            max_retries: Количество попыток при ошибке
        
        Returns:
            Словарь с результатом:
            {
                'success': bool,
                'json': dict или None,
                'raw_response': str,
                'usage': dict,
                'error': str или None
            }
        """
        logger.info(f"🔄 Начало обработки промпта (длина: {len(prompt):,} символов, max_retries: {max_retries})")
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.info(f"🔄 Повторная попытка {attempt}/{max_retries}")
            
            # Создаем временную метку для связанных файлов (промпт и ответ)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Минимальный запрос без ограничений
            response = self._make_request(prompt, save_prompt=(attempt == 0), timestamp=timestamp)
            
            if not response['success']:
                error_type = response.get('error_type', 'unknown')
                error_msg = response.get('error', 'Неизвестная ошибка')
                logger.warning(f"⚠️  Ошибка запроса (попытка {attempt + 1}/{max_retries + 1}, тип: {error_type}): {error_msg[:200]}")
                
                if attempt < max_retries and response.get('error_type') == 'rate_limit':
                    # Ждем перед повтором при rate limit
                    wait_time = (attempt + 1) * 2
                    logger.info(f"⏳ Ожидание {wait_time} секунд перед повтором...")
                    time.sleep(wait_time)
                    continue
                logger.error(f"❌ Обработка промпта завершена с ошибкой после {attempt + 1} попыток")
                return {
                    'success': False,
                    'json': None,
                    'raw_response': None,
                    'usage': None,
                    'error': error_msg
                }
            
            # Извлекаем JSON из ответа
            logger.info(f"🔍 Извлечение JSON из ответа...")
            content = response['content']
            json_data = self.extract_json(content)
            
            if json_data:
                logger.info(f"✅ JSON успешно извлечен (размер: {len(json.dumps(json_data)):,} символов)")
                return {
                    'success': True,
                    'json': json_data,
                    'raw_response': content,
                    'usage': response.get('usage'),
                    'error': None
                }
            else:
                # Если не удалось извлечь JSON, сохраняем ответ для отладки
                logger.warning(f"⚠️  Не удалось извлечь JSON из ответа (попытка {attempt + 1}/{max_retries + 1})")
                debug_file = self._save_debug_response(content, prompt, timestamp)
                
                # Если не удалось извлечь JSON, возвращаем ошибку
                if attempt < max_retries:
                    logger.info(f"🔄 Повторная попытка извлечения JSON...")
                    continue
                logger.error(f"❌ Не удалось извлечь JSON после {max_retries + 1} попыток")
                return {
                    'success': False,
                    'json': None,
                    'raw_response': content,
                    'usage': response.get('usage'),
                    'error': f'Не удалось извлечь валидный JSON из ответа ИИ\n\n'
                            f'📁 Ответ ИИ сохранен для отладки: {debug_file}\n'
                            f'Проверьте файл, чтобы увидеть, что вернула модель.'
                }
        
        return {
            'success': False,
            'json': None,
            'raw_response': None,
            'usage': None,
            'error': 'Превышено количество попыток'
        }
    
    def process_prompt_text(self, prompt: str, max_retries: int = 2) -> Dict[str, Any]:
        """
        Обрабатывает промпт и возвращает текст (не JSON)
        
        Args:
            prompt: Промпт для отправки
            max_retries: Количество попыток при ошибке
        
        Returns:
            Словарь с результатом:
            {
                'success': bool,
                'text': str или None,
                'raw_response': str,
                'usage': dict,
                'error': str или None
            }
        """
        logger.info(f"🔄 Начало обработки текстового промпта (длина: {len(prompt):,} символов, max_retries: {max_retries})")
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.info(f"🔄 Повторная попытка {attempt}/{max_retries}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            response = self._make_request(prompt, save_prompt=(attempt == 0), timestamp=timestamp)
            
            if not response['success']:
                error_type = response.get('error_type', 'unknown')
                error_msg = response.get('error', 'Неизвестная ошибка')
                logger.warning(f"⚠️  Ошибка запроса (попытка {attempt + 1}/{max_retries + 1}, тип: {error_type}): {error_msg[:200]}")
                
                if attempt < max_retries and response.get('error_type') == 'rate_limit':
                    wait_time = (attempt + 1) * 2
                    logger.info(f"⏳ Ожидание {wait_time} секунд перед повтором...")
                    time.sleep(wait_time)
                    continue
                logger.error(f"❌ Обработка текстового промпта завершена с ошибкой после {attempt + 1} попыток")
                return {
                    'success': False,
                    'text': None,
                    'raw_response': None,
                    'usage': None,
                    'error': error_msg
                }
            
            # Возвращаем текст как есть
            content = response['content']
            logger.info(f"✅ Получен текстовый ответ: {len(content):,} символов")
            
            return {
                'success': True,
                'text': content,
                'raw_response': content,
                'usage': response.get('usage'),
                'error': None
            }
        
        return {
            'success': False,
            'text': None,
            'raw_response': None,
            'usage': None,
            'error': 'Превышено количество попыток'
        }


class JayFlowClient:
    """
    Клиент для работы с Jay Flow API
    
    Документация: https://jayflow.ai/help/cards/agent/api.html
    
    Формат запроса:
        GET https://jayflow.ai/channel/api/{channelId}?input={prompt}&threadId={threadId}
    
    Формат ответа:
        {
            "threadId": "681a191ad74ee8d89080289a",
            "content": "Hello! How can I help you today?",  # Markdown или JSON (если включен JSON-режим)
            "messages": [...],
            "images": []
        }
    """
    
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Инициализация клиента
        
        Args:
            api_url: URL API Jay Flow (если None, берется из файла JayFlowClientHTTP.txt)
            api_key: API ключ Jay Flow (если None, берется из файла key.txt или переменной окружения)
        """
        # Загружаем URL из файла
        if api_url:
            self.api_url = api_url
        else:
            self.api_url = self._load_api_url_from_file()
            if not self.api_url:
                raise ValueError(
                    "URL Jay Flow API не найден.\n"
                    "Создайте файл JayFlowClientHTTP.txt в корне проекта и поместите туда URL API."
                )
        
        # Убираем пробелы и переносы строк
        self.api_url = self.api_url.strip()
        
        # Загружаем API ключ
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = self._load_api_key_from_file()
            if not self.api_key:
                self.api_key = os.getenv('JAYFLOW_API_KEY')
        
        # API ключ опционален для Jay Flow
        if self.api_key:
            self.api_key = self.api_key.strip()
        
        # Папки для отладочных файлов
        project_root = Path(__file__).parent.parent
        self.debug_folder = project_root / 'debug'
        self.debug_folder.mkdir(exist_ok=True)
        
        # Отдельные папки для промптов и ответов
        self.debug_prompts_folder = self.debug_folder / 'prompts'
        self.debug_responses_folder = self.debug_folder / 'responses'
        self.debug_prompts_folder.mkdir(exist_ok=True)
        self.debug_responses_folder.mkdir(exist_ok=True)
        
        # Thread ID для продолжения диалога (опционально)
        self.thread_id = None
        
        # Настройка SSL проверки (можно отключить через переменную окружения)
        self.verify_ssl = os.getenv('JAYFLOW_VERIFY_SSL', 'true').lower() not in ('false', '0', 'no')
    
    def _load_api_url_from_file(self) -> Optional[str]:
        """
        Загружает URL API из файла JayFlowClientHTTP.txt
        
        Returns:
            URL API или None, если файл не найден или пуст
        """
        project_root = Path(__file__).parent.parent
        api_url_file = project_root / 'JayFlowClientHTTP.txt'
        
        if not api_url_file.exists():
            return None
        
        try:
            with open(api_url_file, 'r', encoding='utf-8') as f:
                url = f.read().strip()
                if url:
                    return url
        except Exception as e:
            print(f"⚠️  Ошибка чтения JayFlowClientHTTP.txt: {e}")
            return None
        
        return None
    
    def _load_api_key_from_file(self) -> Optional[str]:
        """
        Загружает API ключ из файла key.txt
        
        Returns:
            API ключ или None, если файл не найден или пуст
        """
        project_root = Path(__file__).parent.parent
        api_key_file = project_root / 'key.txt'
        
        if not api_key_file.exists():
            return None
        
        try:
            with open(api_key_file, 'r', encoding='utf-8') as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception as e:
            print(f"⚠️  Ошибка чтения key.txt: {e}")
            return None
        
        return None
    
    def _make_request(self, prompt: str, save_prompt: bool = True, timestamp: str = None) -> Dict[str, Any]:
        """
        Отправляет запрос в Jay Flow API
        
        Args:
            prompt: Текст промпта
            save_prompt: Сохранять ли промпт для отладки
            timestamp: Временная метка для связанных файлов
        
        Returns:
            Ответ от API
        """
        try:
            import requests
        except ImportError:
            raise ImportError(
                "Библиотека requests не установлена. Установите:\n"
                "  pip install requests"
            )
        
        # Сохраняем промпт для отладки (если нужно)
        if save_prompt:
            if timestamp is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._save_debug_prompt(prompt, timestamp)
        elif timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Определяем метод запроса: GET для коротких промптов, POST для длинных
        # GET имеет ограничение на длину URL (~2000 символов), поэтому для больших промптов используем POST
        use_post = len(prompt) > 1500  # Безопасный порог
        
        # Формируем параметры/данные запроса
        # Согласно документации: для нового диалога threadId не передается
        if use_post:
            # Для POST используем JSON body
            data = {
                'input': prompt
            }
            if self.thread_id:
                data['threadId'] = self.thread_id
            params = None
        else:
            # Для GET используем query параметры
            params = {
                'input': prompt
            }
            if self.thread_id:
                params['threadId'] = self.thread_id
            data = None
        
        # Формируем заголовки
        headers = {}
        if self.api_key:
            headers['Authorization'] = self.api_key
        if use_post:
            headers['Content-Type'] = 'application/json'
        
        try:
            # Отправляем запрос с обработкой SSL ошибок и retry
            verify_ssl = self.verify_ssl
            max_retries = 3
            retry_delay = 2  # секунды
            
            for attempt in range(max_retries):
                try:
                    if use_post:
                        # POST запрос с JSON body
                        response = requests.post(
                            self.api_url,
                            json=data,
                            headers=headers if headers else None,
                            timeout=300,  # 5 минут таймаут
                            verify=verify_ssl
                        )
                    else:
                        # GET запрос с query параметрами
                        response = requests.get(
                            self.api_url,
                            params=params,
                            headers=headers if headers else None,
                            timeout=300,  # 5 минут таймаут
                            verify=verify_ssl
                        )
                    # Если успешно, выходим из цикла retry
                    break
                except requests.exceptions.SSLError as ssl_error:
                    # Если SSL ошибка и проверка была включена, пробуем без проверки
                    if verify_ssl and attempt == 0:
                        print("⚠️  SSL ошибка при подключении к Jay Flow API. Пробую без проверки SSL сертификата...")
                        import urllib3
                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                        verify_ssl = False
                        continue  # Повторяем попытку без проверки SSL
                    elif attempt < max_retries - 1:
                        # Если это не первая попытка, ждем и повторяем
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        # Если все попытки исчерпаны, пробрасываем ошибку
                        raise
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_error:
                    # Для ошибок подключения и таймаутов делаем retry
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        print(f"⚠️  Ошибка подключения (попытка {attempt + 1}/{max_retries}). Жду {wait_time} сек...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise
            
            # Проверяем статус ответа
            response.raise_for_status()
            
            # Парсим JSON ответ (согласно документации Jay Flow всегда возвращает JSON)
            result = response.json()
            
            # Сохраняем thread_id для следующих запросов
            if 'threadId' in result:
                self.thread_id = result['threadId']
            
            # Извлекаем контент
            # Согласно документации: content может быть строкой (Markdown) или JSON объектом (если включен JSON-режим)
            content = result.get('content', '')
            
            # Если content - это строка, оставляем как есть
            # Если content - это dict (JSON-режим), конвертируем в строку для дальнейшей обработки
            if isinstance(content, dict):
                # В JSON-режиме content уже является JSON объектом
                # Сохраняем его как строку для извлечения JSON позже
                content = json.dumps(content, ensure_ascii=False)
            
            # Если content пустой, пробуем взять из messages
            if not content and 'messages' in result and result['messages']:
                last_message = result['messages'][-1]
                if isinstance(last_message, dict):
                    content = last_message.get('content', '')
                else:
                    content = str(last_message)
            
            # Сохраняем ответ для отладки
            self._save_debug_response(content, prompt, timestamp)
            
            return {
                'success': True,
                'content': content,
                'thread_id': result.get('threadId'),
                'messages': result.get('messages', []),
                'images': result.get('images', []),
                'usage': None  # Jay Flow не предоставляет информацию об использовании токенов
            }
        
        except requests.exceptions.SSLError as ssl_error:
            error_msg = str(ssl_error)
            
            # Сохраняем ошибку для отладки
            self._save_debug_response(f"SSL ошибка: {error_msg}", prompt, timestamp)
            
            return {
                'success': False,
                'error': (
                    f'SSL ошибка при подключении к Jay Flow API: {error_msg}\n\n'
                    'Возможные решения:\n'
                    '1. Проверьте интернет-соединение\n'
                    '2. Обновите сертификаты: sudo update-ca-certificates (Linux)\n'
                    '3. Проверьте, что URL правильный: https://jayflow.ai/channel/api/{channelId}\n'
                    '4. Попробуйте обновить requests: pip install --upgrade requests urllib3'
                ),
                'error_type': 'ssl_error'
            }
        
        except requests.exceptions.ConnectionError as conn_error:
            error_msg = str(conn_error)
            
            # Сохраняем ошибку для отладки
            self._save_debug_response(f"Ошибка подключения: {error_msg}", prompt, timestamp)
            
            return {
                'success': False,
                'error': (
                    f'Ошибка подключения к Jay Flow API: {error_msg}\n\n'
                    'Возможные причины:\n'
                    '1. Нет интернет-соединения\n'
                    '2. Неправильный URL API\n'
                    '3. Сервер Jay Flow недоступен\n'
                    f'Проверьте URL: {self.api_url}'
                ),
                'error_type': 'connection_error'
            }
        
        except requests.exceptions.Timeout as timeout_error:
            error_msg = str(timeout_error)
            
            # Сохраняем ошибку для отладки
            self._save_debug_response(f"Таймаут: {error_msg}", prompt, timestamp)
            
            return {
                'success': False,
                'error': (
                    f'Таймаут при запросе к Jay Flow API: {error_msg}\n\n'
                    'Запрос занял слишком много времени (>5 минут).\n'
                    'Возможно, промпт слишком большой или сервер перегружен.'
                ),
                'error_type': 'timeout'
            }
        
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            
            # Сохраняем ошибку для отладки
            self._save_debug_response(f"Ошибка запроса: {error_msg}", prompt, timestamp)
            
            return {
                'success': False,
                'error': f'Ошибка запроса к Jay Flow API: {error_msg}',
                'error_type': 'api_error'
            }
        
        except Exception as e:
            error_msg = str(e)
            self._save_debug_response(f"Неожиданная ошибка: {error_msg}", prompt, timestamp)
            
            return {
                'success': False,
                'error': f'Неожиданная ошибка: {error_msg}',
                'error_type': 'unknown'
            }
    
    def _save_debug_prompt(self, prompt: str, timestamp: str = None) -> str:
        """
        Сохраняет промпт в файл для отладки
        
        Args:
            prompt: Промпт для отправки в ИИ
            timestamp: Временная метка (если None, генерируется автоматически)
        
        Returns:
            Путь к сохраненному файлу
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        prompt_file = self.debug_prompts_folder / f"prompt_jayflow_{timestamp}.txt"
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"ОТЛАДОЧНЫЙ ФАЙЛ - Промпт для Jay Flow API\n")
            f.write(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"API URL: {self.api_url}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("ПРОМПТ:\n")
            f.write("-" * 80 + "\n")
            f.write(prompt)
            f.write("\n" + "-" * 80 + "\n\n")
            
            f.write("ИНФОРМАЦИЯ:\n")
            f.write(f"Длина промпта: {len(prompt)} символов\n")
            estimated_tokens = len(prompt) // 4
            f.write(f"Примерное количество токенов: ~{estimated_tokens}\n")
        
        return str(prompt_file)
    
    def _save_debug_response(self, content: str, prompt: str = None, timestamp: str = None) -> str:
        """
        Сохраняет ответ ИИ в файл для отладки
        
        Args:
            content: Содержимое ответа от ИИ
            prompt: Промпт (опционально, для ссылки на файл промпта)
            timestamp: Временная метка (если None, генерируется автоматически)
        
        Returns:
            Путь к сохраненному файлу
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        response_file = self.debug_responses_folder / f"response_jayflow_{timestamp}.txt"
        
        with open(response_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"ОТЛАДОЧНЫЙ ФАЙЛ - Ответ Jay Flow API\n")
            f.write(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"API URL: {self.api_url}\n")
            if prompt:
                prompt_file = self.debug_prompts_folder / f"prompt_jayflow_{timestamp}.txt"
                f.write(f"Связанный промпт: {prompt_file}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("ОТВЕТ ИИ:\n")
            f.write("-" * 80 + "\n")
            f.write(content if content else "(пустой ответ)")
            f.write("\n" + "-" * 80 + "\n\n")
            
            f.write("ИНФОРМАЦИЯ:\n")
            f.write(f"Длина ответа: {len(content)} символов\n")
            if content:
                f.write(f"Первые 200 символов: {content[:200]}\n")
                f.write(f"Последние 200 символов: {content[-200:]}\n")
            else:
                f.write("Ответ пустой!\n")
        
        return str(response_file)
    
    def extract_json(self, text: str) -> Optional[dict]:
        """
        Извлекает JSON из текста ответа
        
        Args:
            text: Текст ответа от ИИ
        
        Returns:
            Распарсенный JSON или None
        """
        # Jay Flow может возвращать JSON напрямую, если включен JSON-режим
        # Пытаемся найти JSON в тексте
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',  # JSON в блоке кода
            r'```\s*(\{.*?\})\s*```',      # JSON в блоке без указания языка
            r'(\{.*\})',                    # Просто JSON объект
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                try:
                    return json.loads(matches[0])
                except json.JSONDecodeError:
                    continue
        
        # Если ничего не найдено, пытаемся распарсить весь текст
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    def process_prompt(self, prompt: str, max_retries: int = 2) -> Dict[str, Any]:
        """
        Обрабатывает промпт и возвращает заполненный JSON
        
        Args:
            prompt: Промпт для отправки
            max_retries: Количество попыток при ошибке
        
        Returns:
            Словарь с результатом:
            {
                'success': bool,
                'json': dict или None,
                'raw_response': str,
                'usage': dict,
                'error': str или None
            }
        """
        for attempt in range(max_retries + 1):
            # Создаем временную метку для связанных файлов (промпт и ответ)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Отправляем запрос
            response = self._make_request(prompt, save_prompt=(attempt == 0), timestamp=timestamp)
            
            if not response['success']:
                if attempt < max_retries:
                    # Ждем перед повтором
                    wait_time = (attempt + 1) * 2
                    time.sleep(wait_time)
                    continue
                return {
                    'success': False,
                    'json': None,
                    'raw_response': None,
                    'usage': None,
                    'error': response.get('error', 'Неизвестная ошибка')
                }
            
            # Извлекаем JSON из ответа
            content = response['content']
            json_data = self.extract_json(content)
            
            if json_data:
                return {
                    'success': True,
                    'json': json_data,
                    'raw_response': content,
                    'usage': None,  # Jay Flow не предоставляет информацию об использовании токенов
                    'error': None
                }
            else:
                # Если не удалось извлечь JSON, сохраняем ответ для отладки
                debug_file = self._save_debug_response(content, prompt, timestamp)
                
                # Если не удалось извлечь JSON, возвращаем ошибку
                if attempt < max_retries:
                    continue
                return {
                    'success': False,
                    'json': None,
                    'raw_response': content,
                    'usage': None,
                    'error': (
                        'Не удалось извлечь валидный JSON из ответа Jay Flow API.\n\n'
                        'Возможные причины:\n'
                        '1. Агент не вернул JSON в ответе\n'
                        '2. Включите JSON-режим в настройках агента Jay Flow\n'
                        '3. Проверьте промпт - он должен явно запрашивать JSON\n\n'
                        f'📁 Полный ответ сохранен для отладки: {debug_file}'
                    ),
                    'error_type': 'json_extraction_error'
                }
        
        return {
            'success': False,
            'json': None,
            'raw_response': None,
            'usage': None,
            'error': 'Превышено количество попыток'
        }
    
    def process_prompt_text(self, prompt: str, max_retries: int = 2) -> Dict[str, Any]:
        """
        Обрабатывает промпт и возвращает текст (не JSON)
        
        Args:
            prompt: Промпт для отправки
            max_retries: Количество попыток при ошибке
        
        Returns:
            Словарь с результатом:
            {
                'success': bool,
                'text': str или None,
                'raw_response': str,
                'usage': dict,
                'error': str или None
            }
        """
        for attempt in range(max_retries + 1):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            response = self._make_request(prompt, save_prompt=(attempt == 0), timestamp=timestamp)
            
            if not response['success']:
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 2
                    time.sleep(wait_time)
                    continue
                return {
                    'success': False,
                    'text': None,
                    'raw_response': None,
                    'usage': None,
                    'error': response.get('error', 'Неизвестная ошибка')
                }
            
            # Возвращаем текст как есть
            content = response['content']
            
            return {
                'success': True,
                'text': content,
                'raw_response': content,
                'usage': None,  # Jay Flow не предоставляет информацию об использовании токенов
                'error': None
            }
        
        return {
            'success': False,
            'text': None,
            'raw_response': None,
            'usage': None,
            'error': 'Превышено количество попыток'
        }

