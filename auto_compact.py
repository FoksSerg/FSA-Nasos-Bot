#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматический создатель компактных версий RouterOS скриптов
Автор: Фокин Сергей Александрович
Дата: 24 июня 2025

Скрипт автоматически запускается при импорте или выполнении
"""

import os
import sys
import re
from pathlib import Path

def remove_comments(line):
    """Удаляет комментарии из строки RouterOS"""
    if line.strip().startswith('#'):
        return ''
    
    in_string = False
    quote_char = None
    i = 0
    
    while i < len(line):
        char = line[i]
        
        if char in ['"', "'"]:
            if not in_string:
                in_string = True
                quote_char = char
            elif char == quote_char:
                if i == 0 or line[i-1] != '\\':
                    in_string = False
                    quote_char = None
        elif char == '#' and not in_string:
            return line[:i].rstrip()
        
        i += 1
    
    return line

def compact_routeros_file(input_file, output_file):
    """Создает компактную версию RouterOS файла"""
    try:
        if not os.path.exists(input_file):
            return False, f"Файл не найден: {input_file}", 0, 0
        
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_size = sum(len(line.encode('utf-8')) for line in lines)
        
        compact_lines = []
        for line in lines:
            line = remove_comments(line)
            line = line.lstrip().rstrip()
            if line:
                compact_lines.append(line + '\n')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(compact_lines)
        
        compact_size = sum(len(line.encode('utf-8')) for line in compact_lines)
        
        return True, f"Создан: {output_file}", original_size, compact_size
        
    except Exception as e:
        return False, f"Ошибка: {str(e)}", 0, 0

def auto_process_project():
    """Автоматически обрабатывает все .rsc файлы проекта"""
    code_nasos_dir = Path("CodeNasos")
    code_nasos_dir.mkdir(exist_ok=True)
    
    current_dir = Path(".")
    rsc_files = list(current_dir.glob("*.rsc"))
    
    project_modules = []
    for file_path in rsc_files:
        filename = file_path.name
        if ("-Compact" not in filename and 
            not filename.startswith("Test-") and
            filename.startswith("Nasos-")):
            project_modules.append(file_path)
    
    if not project_modules:
        return [(False, "Модули проекта Nasos-*.rsc не найдены", 0, 0)]
    
    results = []
    for module_path in project_modules:
        output_path = code_nasos_dir / module_path.name
        success, message, orig_size, comp_size = compact_routeros_file(
            str(module_path), str(output_path))
        results.append((success, message, orig_size, comp_size))
    
    return results

def format_size(size_bytes):
    """Форматирует размер в удобочитаемый вид"""
    if size_bytes < 1024:
        return f"{size_bytes} байт"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def calculate_savings(original, compact):
    """Вычисляет экономию места"""
    if original == 0:
        return 0
    return ((original - compact) / original) * 100

def run_auto_compact():
    """Основная функция автоматической обработки"""
    print("=== Автоматический создатель компактных RouterOS скриптов ===")
    print("Автор: Фокин Сергей Александрович")
    print("Дата: 24 июня 2025")
    print()
    print("🔄 Автоматическая обработка модулей проекта NasosRunner...")
    print("📁 Создание компактных версий в папке CodeNasos/")
    print("-" * 80)
    
    results = auto_process_project()
    
    total_original = 0
    total_compact = 0
    success_count = 0
    
    for success, message, orig_size, comp_size in results:
        print(f"{'✓' if success else '✗'} {message}")
        
        if success:
            print(f"  Оригинал: {format_size(orig_size)} → Компакт: {format_size(comp_size)} "
                  f"(экономия {calculate_savings(orig_size, comp_size):.1f}%)")
            total_original += orig_size
            total_compact += comp_size
            success_count += 1
        
        print()
    
    if success_count > 0:
        print("-" * 80)
        print(f"✅ ИТОГО обработано модулей: {success_count}")
        print(f"📊 Общий размер оригиналов: {format_size(total_original)}")
        print(f"📦 Общий размер компактных: {format_size(total_compact)}")
        print(f"💾 Общая экономия: {format_size(total_original - total_compact)} "
              f"({calculate_savings(total_original, total_compact):.1f}%)")
        print()
        print("🎯 Компактные модули готовы для загрузки в Winbox!")
    else:
        print("❌ Не удалось обработать ни одного модуля")

# АВТОЗАПУСК при выполнении скрипта
if __name__ == "__main__":
    run_auto_compact()
    
    # Пауза для просмотра результатов
    input("\nНажмите Enter для выхода...")

# АВТОЗАПУСК при импорте (раскомментировать если нужно)
run_auto_compact() 