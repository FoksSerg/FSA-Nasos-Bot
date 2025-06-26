#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматический создатель компактных версий RouterOS скриптов (ПРОСТОЙ АЛГОРИТМ)
Автор: Фокин Сергей Александрович
Дата: 24 июня 2025

Простой алгоритм:
1. если строка начинается с # - удаляем всю строку
2. если строка пустая - удаляем  
3. если есть отступы или пробелы в начале строки - удаляем отступы и пробелы
4. если в конце строки нет ; и не заканчивается на \r\ - добавляем в конце ;
5. если в конце строк \r\ - ничего не делаем
"""

import os
import sys
from pathlib import Path



def process_line(line):
    """Обрабатывает одну строку согласно простому алгоритму"""
    
    # 1. если строка начинается с # - удаляем всю строку
    if line.strip().startswith('#'):
        return None
    
    # 2. если строка пустая - удаляем
    if not line.strip():
        return None
    
    # 3. если есть отступы или пробелы в начале строки - удаляем отступы и пробелы
    line = line.lstrip()
    
    # 4. если в конце строки нет ; и не заканчивается на \r\ - добавляем в конце ;
    stripped = line.rstrip()
    if not stripped.endswith(';') and not stripped.endswith('\\r\\'):
        # ИСКЛЮЧЕНИЕ: не добавляем ; к пустым блокам on-error и других специальных конструкций
        # а также к строкам заканчивающимся на } или {
        if not stripped.endswith('{}') and not stripped.endswith('do={') and not stripped.endswith('}') and not stripped.endswith('{'):
            line = stripped + ';\n'
        else:
            line = line.rstrip() + '\n'
    else:
        # 5. если в конце строк \r\ - ничего не делаем
        line = line.rstrip() + '\n'
    
    return line

def compact_routeros_file(input_file, output_file):
    """Создает компактную версию RouterOS файла"""
    try:
        # Преобразуем Path объекты в строки если нужно
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        if not input_path.exists():
            return False, f"Файл не найден: {input_path}", 0, 0, 0
        
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_size = sum(len(line.encode('utf-8')) for line in lines)
        syntax_fixes = 0
        
        compact_lines = []
        for line in lines:
            processed_line = process_line(line)
            
            if processed_line is not None:
                # Считаем количество исправлений (добавление ;)
                if not line.rstrip().endswith(';') and processed_line.rstrip().endswith(';'):
                    syntax_fixes += 1
                
                compact_lines.append(processed_line)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(compact_lines)
        
        compact_size = sum(len(line.encode('utf-8')) for line in compact_lines)
        
        return True, f"Создан: {output_path}", original_size, compact_size, syntax_fixes
        
    except Exception as e:
        return False, f"Ошибка: {str(e)}", 0, 0, 0

def auto_process_project():
    """Автоматически обрабатывает все .rsc файлы проекта"""
    # Получаем директорию где лежит сам скрипт (исходные файлы на том же уровне)
    script_dir = Path(__file__).parent
    
    # Создаем папку CodeNasos рядом со скриптом
    code_nasos_dir = script_dir / "CodeNasos"
    code_nasos_dir.mkdir(exist_ok=True)
    
    # Ищем .rsc файлы в директории скрипта (на том же уровне)
    rsc_files = list(script_dir.glob("*.rsc"))
    
    project_modules = []
    for file_path in rsc_files:
        filename = file_path.name
        if ("-Compact" not in filename and 
            not filename.startswith("Test-") and
            filename.startswith("Nasos-")):
            project_modules.append(file_path)
    
    if not project_modules:
        return [(False, "Модули проекта Nasos-*.rsc не найдены на том же уровне", 0, 0, 0)]
    
    results = []
    for module_path in project_modules:
        output_path = code_nasos_dir / module_path.name
        success, message, orig_size, comp_size, fixes = compact_routeros_file(
            module_path, output_path)
        results.append((success, message, orig_size, comp_size, fixes))
    
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
    print("=== Автоматический создатель компактных RouterOS скриптов (ПРОСТОЙ АЛГОРИТМ) ===")
    print("Автор: Фокин Сергей Александрович")
    print("Дата: 24 июня 2025")
    print()
    print("🔄 Простой алгоритм компактирования:")
    print("   1. Удаление комментариев (строки с #)")
    print("   2. Удаление пустых строк")
    print("   3. Удаление отступов и пробелов в начале")
    print("   4. Добавление ; если нет и строка не заканчивается на \\r\\")
    print("   5. Сохранение строк с \\r\\ без изменений")
    print()
    print("📁 Создание компактных версий в папке CodeNasos/")
    print("-" * 80)
    
    results = auto_process_project()
    
    total_original = 0
    total_compact = 0
    total_fixes = 0
    success_count = 0
    
    for success, message, orig_size, comp_size, fixes in results:
        print(f"{'✓' if success else '✗'} {message}")
        
        if success:
            print(f"  Оригинал: {format_size(orig_size)} → Компакт: {format_size(comp_size)} "
                  f"(экономия {calculate_savings(orig_size, comp_size):.1f}%)")
            
            if fixes > 0:
                print(f"  🔧 Добавлено ; к командам: {fixes}")
            
            total_original += orig_size
            total_compact += comp_size
            total_fixes += fixes
            success_count += 1
        
        print()
    
    if success_count > 0:
        print("-" * 80)
        print(f"✅ ИТОГО обработано модулей: {success_count}")
        print(f"📊 Общий размер оригиналов: {format_size(total_original)}")
        print(f"📦 Общий размер компактных: {format_size(total_compact)}")
        print(f"💾 Общая экономия: {format_size(total_original - total_compact)} "
              f"({calculate_savings(total_original, total_compact):.1f}%)")
        
        if total_fixes > 0:
            print(f"🔧 Всего добавлено ; к командам: {total_fixes}")
        
        print()
        print("🎯 Компактные модули готовы для загрузки в Winbox!")
    else:
        print("❌ Не удалось обработать ни одного модуля")

# АВТОЗАПУСК при выполнении скрипта
if __name__ == "__main__":
    run_auto_compact()
