#!/usr/bin/env python3
"""
Простой скрипт для конвертации документов
Использование: python convert_document.py <файл>

Для использования активируйте виртуальное окружение:
  source venv/bin/activate
"""

import sys
import os
from pathlib import Path

# Проверка виртуального окружения
venv_path = Path(__file__).parent / "venv"
if not venv_path.exists():
    print("⚠️  Виртуальное окружение не найдено!")
    print("   Создайте его: python3 -m venv venv")
    print("   Активируйте: source venv/bin/activate")
    print("   Установите зависимости: pip install -r requirements.txt")
    sys.exit(1)

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from document_converter import DocumentConverter

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python convert_document.py <файл> [-o output.txt]")
        print("\nПримеры:")
        print("  python convert_document.py document.pdf")
        print("  python convert_document.py report.docx -o output.txt")
        print("  python convert_document.py data.xlsx")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] == '-o' else None
    if output_file == '-o' and len(sys.argv) > 3:
        output_file = sys.argv[3]
    elif output_file == '-o':
        output_file = None
    
    try:
        converter = DocumentConverter()
        result = converter.convert(input_file, output_file)
        print(f"\n✅ Успешно! Файл сохранен: {result}")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

