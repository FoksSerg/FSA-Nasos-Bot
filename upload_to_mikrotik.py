#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MikroTik Module Uploader - быстрый запуск
Использование: python3 upload_to_mikrotik.py [опции]
"""

import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADER_SCRIPT = os.path.join(SCRIPT_DIR, "MikrotikUploader", "mikrotik_uploader.py")
REQUIREMENTS_FILE = os.path.join(SCRIPT_DIR, "MikrotikUploader", "requirements_uploader.txt")

# Цвета для вывода
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

print(f"{BLUE}🤖 MikroTik Module Uploader{NC}")
print("==================================")

# Проверка Python
if not sys.version_info >= (3, 6):
    print(f"{RED}❌ Требуется Python 3.6 или выше{NC}")
    sys.exit(1)

# Проверка зависимостей
try:
    print("🔍 Проверяю зависимости...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
    print(f"{GREEN}✅ Все зависимости найдены{NC}")
except:
    print(f"{RED}❌ Ошибка установки зависимостей{NC}")
    sys.exit(1)

# Проверка наличия модулей
MODULES_DIR = os.path.join(SCRIPT_DIR, "CodeNasos")
if not os.path.isdir(MODULES_DIR):
    print(f"{RED}❌ Папка с модулями не найдена{NC}")
    sys.exit(1)

modules = [f for f in os.listdir(MODULES_DIR) if f.endswith('.rsc')]
print(f"📦 Найдено модулей:       {len(modules)}")

# Запуск загрузчика
print("🚀 Запускаю загрузчик...")
try:
    subprocess.run([sys.executable, UPLOADER_SCRIPT] + sys.argv[1:], check=True)
    print(f"{GREEN}🎉 Загрузчик завершился успешно!{NC}")
except KeyboardInterrupt:
    print(f"\n{YELLOW}⚠️ Прервано пользователем{NC}")
except subprocess.CalledProcessError:
    print(f"{RED}❌ Ошибка выполнения загрузчика{NC}")
    sys.exit(1)
except FileNotFoundError:
    print(f"{RED}❌ Ошибка: Скрипт загрузчика не найден{NC}")
    sys.exit(1) 