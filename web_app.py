#!/usr/bin/env python3
"""
Веб-интерфейс для конвертации документов и заполнения ТЗ через ИИ
Запуск: python web_app.py
"""

from flask import Flask, render_template, request, send_file, jsonify, flash
from werkzeug.utils import secure_filename
import os
import json
from pathlib import Path
import sys

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from document_converter import DocumentConverter
from prompt_builder import PromptBuilder
from ai_client import OpenAIClient, JayFlowClient
from json_to_excel import JSONToExcelConverter

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'converted'
app.config['RESULTS_FOLDER'] = 'results'

# Создаем папки для загрузок и результатов
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
Path(app.config['OUTPUT_FOLDER']).mkdir(exist_ok=True)
Path(app.config['RESULTS_FOLDER']).mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

def allowed_file(filename):
    """Проверяет, разрешен ли формат файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки, конвертации и заполнения ТЗ через ИИ"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не выбран'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'error': f'Неподдерживаемый формат. Разрешены: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400
    
    try:
        # Шаг 1: Сохраняем загруженный файл
        filename = secure_filename(file.filename)
        upload_path = Path(app.config['UPLOAD_FOLDER']) / filename
        file.save(str(upload_path))
        
        # Шаг 2: Конвертируем документ в текст
        converter = DocumentConverter()
        converted_filename = f"{Path(filename).stem}_converted.txt"
        converted_path = converter.convert(
            str(upload_path),
            str(Path(app.config['OUTPUT_FOLDER']) / converted_filename)
        )
        
        # Читаем сконвертированный текст
        with open(converted_path, 'r', encoding='utf-8') as f:
            converted_text = f.read()
        
        # Шаг 3: Строим промпт
        try:
            prompt_builder = PromptBuilder()
            final_prompt = prompt_builder.build_prompt(converted_text)
        except Exception as e:
            return jsonify({
                'error': f'Ошибка построения промпта: {str(e)}'
            }), 500
        
        # Шаг 4: Отправляем в AI API (OpenAI или Jay Flow)
        try:
            # Получаем выбор AI из запроса
            ai_provider = request.form.get('ai_provider', 'openai').lower()
            
            if ai_provider == 'jayflow':
                ai_client = JayFlowClient()
            else:
                ai_client = OpenAIClient()
            
            result = ai_client.process_prompt(final_prompt)
            
            if not result['success']:
                return jsonify({
                    'error': f'Ошибка ИИ: {result.get("error", "Неизвестная ошибка")}',
                    'stage': 'ai_processing'
                }), 500
            
            # Шаг 5: Сохраняем результат в JSON
            result_filename = f"{Path(filename).stem}_filled.json"
            result_path = Path(app.config['RESULTS_FOLDER']) / result_filename
            
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result['json'], f, ensure_ascii=False, indent=2)
            
            # Шаг 6: Конвертируем JSON в Excel
            excel_filename = f"{Path(filename).stem}_filled.xlsx"
            excel_path = Path(app.config['RESULTS_FOLDER']) / excel_filename
            
            try:
                converter = JSONToExcelConverter()
                converter.convert(result['json'], str(excel_path))
                excel_size = os.path.getsize(excel_path)
                excel_available = True
            except Exception as e:
                print(f"⚠️  Ошибка создания Excel файла: {e}")
                excel_available = False
                excel_size = 0
            
            # Информация об использовании токенов
            usage_info = result.get('usage', {})
            
            return jsonify({
                'success': True,
                'message': 'ТЗ успешно заполнено с помощью ИИ',
                'filename': result_filename,
                'size': os.path.getsize(result_path),
                'download_url': f'/download_result/{result_filename}',
                'excel_filename': excel_filename if excel_available else None,
                'excel_size': excel_size if excel_available else 0,
                'excel_download_url': f'/download_result/{excel_filename}' if excel_available else None,
                'usage': {
                    'prompt_tokens': usage_info.get('prompt_tokens', 0),
                    'completion_tokens': usage_info.get('completion_tokens', 0),
                    'total_tokens': usage_info.get('total_tokens', 0)
                }
            })
        
        except ValueError as e:
            # Ошибка с API ключом
            return jsonify({
                'error': str(e),
                'stage': 'ai_setup'
            }), 500
        except ImportError as e:
            return jsonify({
                'error': str(e),
                'stage': 'ai_setup'
            }), 500
        except Exception as e:
            return jsonify({
                'error': f'Ошибка обработки ИИ: {str(e)}',
                'stage': 'ai_processing'
            }), 500
    
    except Exception as e:
        return jsonify({
            'error': f'Ошибка обработки: {str(e)}',
            'stage': 'conversion'
        }), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Скачивание сконвертированного текстового файла"""
    file_path = Path(app.config['OUTPUT_FOLDER']) / secure_filename(filename)
    
    if not file_path.exists():
        return jsonify({'error': 'Файл не найден'}), 404
    
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=filename,
        mimetype='text/plain'
    )

@app.route('/download_result/<filename>')
def download_result(filename):
    """Скачивание заполненного JSON или Excel файла"""
    file_path = Path(app.config['RESULTS_FOLDER']) / secure_filename(filename)
    
    if not file_path.exists():
        return jsonify({'error': 'Файл не найден'}), 404
    
    # Определяем MIME тип по расширению
    if filename.endswith('.xlsx'):
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif filename.endswith('.json'):
        mimetype = 'application/json'
    else:
        mimetype = 'application/octet-stream'
    
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )

@app.route('/health')
def health():
    """Проверка работоспособности"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("=" * 60)
    print("🌐 Веб-интерфейс для заполнения ТЗ через ИИ")
    print("=" * 60)
    print("📂 Загрузки: uploads/")
    print("📄 Конвертированные: converted/")
    print("✅ Результаты: results/")
    print("🌍 Откройте в браузере: http://127.0.0.1:5000")
    print()
    
    # Проверка API ключа
    api_key = None
    
    # Сначала пробуем прочитать из файла
    api_key_file = Path(__file__).parent / 'key.txt'
    if api_key_file.exists():
        try:
            with open(api_key_file, 'r', encoding='utf-8') as f:
                api_key = f.read().strip()
            if api_key:
                print(f"✅ OpenAI API ключ найден в key.txt (первые 10 символов: {api_key[:10]}...)")
        except Exception as e:
            print(f"⚠️  Ошибка чтения key.txt: {e}")
    
    # Если не нашли в файле, пробуем переменную окружения
    if not api_key:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            print(f"✅ OpenAI API ключ найден в переменной окружения (первые 10 символов: {api_key[:10]}...)")
        else:
            print("⚠️  API ключ не найден!")
            print("   Создайте файл ApiKey.txt в корне проекта или установите:")
            print("   export OPENAI_API_KEY='your-key-here'")
    
    print("=" * 60)
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)

