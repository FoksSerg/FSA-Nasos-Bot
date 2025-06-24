#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Удобная обертка для запуска MikroTik Uploader
Поддерживает все те же аргументы командной строки
"""

import os
import sys
import subprocess

def main():
    # Получаем путь к директории скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    uploader_script = os.path.join(script_dir, "MikrotikUploader", "upload_to_mikrotik.sh")
    
    # Проверяем наличие скрипта
    if not os.path.isfile(uploader_script):
        print("❌ Ошибка: Скрипт загрузчика не найден")
        sys.exit(1)
    
    try:
        # Запускаем загрузчик с теми же аргументами
        result = subprocess.run(["/bin/bash", uploader_script] + sys.argv[1:], 
                              cwd=script_dir)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n⚠️ Прервано пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Ошибка при запуске загрузчика: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 