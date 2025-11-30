# Миграция на новую архитектуру

## Что изменилось

### Старая структура:
```
src/
  - ai_client.py (OpenAI + JayFlow)
  - document_converter.py
  - prompt_builder.py
  - json_to_excel.py
web_app.py (все маршруты в одном файле)
```

### Новая структура:
```
app/
  - routes/ (разделены по функциональности)
  - services/ (бизнес-логика)
  - core/ (переиспользуемые компоненты)
  - utils/ (утилиты)
run.py (новая точка входа)
```

## Шаги миграции

### 1. Разделить ai_client.py

Нужно разделить `src/ai_client.py` на два файла:
- `app/core/ai/openai_client.py` - класс OpenAIClient
- `app/core/ai/jayflow_client.py` - класс JayFlowClient

Оба должны наследоваться от `BaseAIClient` в `app/core/ai/base.py`

### 2. Обновить пути в AI клиентах

В новых файлах обновить пути:
- `project_root = Path(__file__).parent.parent.parent` (вместо parent.parent)
- `debug_folder = project_root / 'storage' / 'debug'`
- `api_key_file = project_root / 'key.txt'`

### 3. Обновить web_app.py (опционально)

Старый `web_app.py` можно оставить для обратной совместимости или удалить после миграции.

### 4. Переместить данные

Убедиться, что файлы перемещены:
- `Промпт.txt` → `data/Промпт.txt`
- `TZ.json` → `data/TZ.json`
- `glossary.json` → `data/glossary.json`

## Быстрый старт после миграции

```bash
# Активировать виртуальное окружение
source venv/bin/activate

# Запустить новое приложение
python run.py
```

## Обратная совместимость

Старый `web_app.py` можно оставить для постепенной миграции. Он будет работать параллельно с новой структурой.

