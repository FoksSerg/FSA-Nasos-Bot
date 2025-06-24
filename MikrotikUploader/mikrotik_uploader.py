#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MikroTik Router Uploader
Автоматическая загрузка модулей RouterOS в MikroTik через SSH/SFTP

Требования:
- pip install paramiko

Использование:
python3 mikrotik_uploader.py
"""

import os
import sys
import json
import time
import getpass
import argparse
from pathlib import Path
import paramiko
from paramiko import SSHClient, SFTPClient
from typing import List, Dict, Optional

# Настройки
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "mikrotik_config.json")

# Цвета для вывода
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

class Colors:
    """ANSI цвета для консоли"""
    RED = RED
    GREEN = GREEN
    YELLOW = YELLOW
    BLUE = BLUE
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = NC

class MikroTikUploader:
    def __init__(self):
        self.config = self.load_config()
        self.ssh_client = None
        self.sftp_client = None
        
    def load_config(self) -> Dict:
        """Загружает конфигурацию из файла"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {
            "router_ip": "",
            "username": "admin",
            "password": "",
            "port": 22,
            "source_dir": "../CodeNasos",
            "remote_upload_dir": "/",
            "modules": [
                "Nasos-Runner.rsc",
                "Nasos-Telegram.rsc", 
                "Nasos-Messages.rsc",
                "Nasos-TG-Activator.rsc",
                "Nasos-TG-Poller.rsc",
                "Nasos-TG-SendKeyboard.rsc",
                "Nasos-TG-MenuSet.rsc",
                "Nasos-TimeUtils.rsc",
                "Nasos-TG-SendReplyKeyboard.rsc",
                "Nasos-WatchDog.rsc",
                "Nasos-Startup.rsc",
                "Nasos-TG-MenuClear.rsc",
                "Nasos-TG-SendMessage.rsc"
            ]
        }
    
    def save_config(self):
        """Сохраняет конфигурацию в файл"""
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def setup_connection(self):
        """Настройка подключения"""
        print(f"{Colors.CYAN}🔧 Настройка подключения к MikroTik{Colors.END}")
        
        # IP адрес
        default_ip = self.config.get("router_ip", "")
        ip = input(f"IP адрес [{default_ip}]: ").strip()
        if ip:
            self.config["router_ip"] = ip
        elif not default_ip:
            print(f"{RED}❌ IP адрес обязателен{NC}")
            sys.exit(1)

        # Имя пользователя
        default_user = self.config.get("username", "admin")
        username = input(f"Имя пользователя [{default_user}]: ").strip()
        if username:
            self.config["username"] = username
        
        # Пароль
        if self.config.get("password"):
            change = input("Изменить сохраненный пароль? (y/N): ").lower() == 'y'
            if change:
                self.config["password"] = input("Введите пароль: ").strip()
        else:
            self.config["password"] = input("Введите пароль: ").strip()

        # Порт SSH
        default_port = self.config.get("port", 22)
        port = input(f"Порт SSH [{default_port}]: ").strip()
        if port:
            self.config["port"] = int(port)

        self.save_config()
        print(f"{GREEN}✅ Настройки сохранены{NC}")
    
    def connect(self):
        """Подключение к MikroTik через SSH"""
        try:
            print(f"{Colors.BLUE}🔗 Подключение к {self.config['router_ip']}:{self.config['port']}...{Colors.END}")
            
            self.ssh_client = SSHClient()
            self.ssh_client.load_system_host_keys()
            # Используем WarningPolicy для безопасности, но с возможностью подключения
            self.ssh_client.set_missing_host_key_policy(paramiko.WarningPolicy())
            
            self.ssh_client.connect(
                hostname=self.config['router_ip'],
                port=self.config['port'],
                username=self.config['username'],
                password=self.config['password'],
                timeout=10,
                allow_agent=False,  # Отключаем SSH агент
                look_for_keys=False  # Отключаем поиск ключей
            )
            
            self.sftp_client = self.ssh_client.open_sftp()
            print(f"{Colors.GREEN}✅ Подключение установлено{Colors.END}")
            return True
            
        except Exception as e:
            print(f"{RED}❌ Ошибка подключения: {e}{NC}")
            self.disconnect()  # Закрываем соединение при ошибке
            return False
    
    def disconnect(self):
        """Отключение от MikroTik"""
        try:
            if self.sftp_client:
                try:
                    self.sftp_client.close()
                except:
                    pass
                self.sftp_client = None
                
            if self.ssh_client:
                try:
                    for session in self.ssh_client._transport.getpeername():
                        try:
                            session.close()
                        except:
                            pass
                    self.ssh_client.close()
                except:
                    pass
                self.ssh_client = None
                
            print(f"{Colors.BLUE}🔌 Отключено от MikroTik{Colors.END}")
        except Exception as e:
            print(f"{YELLOW}⚠️ Ошибка при отключении: {e}{NC}")
    
    def execute_command(self, command):
        """Выполнение команды на MikroTik"""
        try:
            if not self.ssh_client or not self.ssh_client.get_transport() or not self.ssh_client.get_transport().is_active():
                print(f"{YELLOW}⚠️ Переподключение к MikroTik...{NC}")
                if not self.connect():
                    return False, "Ошибка подключения"
                    
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=30)
            result = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            
            # Закрываем каналы
            stdin.close()
            stdout.close()
            stderr.close()
            
            if error:
                print(f"{RED}❌ Ошибка выполнения команды: {error}{NC}")
                return False, error
            
            return True, result
            
        except Exception as e:
            print(f"{RED}❌ Ошибка SSH команды: {e}{NC}")
            self.disconnect()  # Закрываем соединение при ошибке
            return False, str(e)
    
    def upload_file(self, local_path, remote_path):
        """Загрузка файла через SFTP"""
        try:
            self.sftp_client.put(local_path, remote_path)
            return True
        except Exception as e:
            print(f"{RED}❌ Ошибка загрузки файла: {e}{NC}")
            return False
    
    def create_script_from_file(self, script_name, local_file_path):
        """Создание скрипта в RouterOS из локального файла"""
        try:
            # Читаем содержимое файла
            with open(local_file_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            
            # Экранируем специальные символы для RouterOS
            script_content = script_content.replace('\\', '\\\\')
            script_content = script_content.replace('"', '\\"')
            script_content = script_content.replace('\n', '\\n')
            
            # Создаем скрипт
            command = f'/system script add name="{script_name}" source="{script_content}"'
            
            # Сначала удаляем существующий скрипт если есть
            delete_cmd = f'/system script remove [find name="{script_name}"]'
            self.execute_command(delete_cmd)
            
            # Создаем новый скрипт
            success, result = self.execute_command(command)
            return success
            
        except Exception as e:
            print(f"{RED}❌ Ошибка создания скрипта: {e}{NC}")
            return False
    
    def get_available_modules(self) -> List[Dict]:
        """Получение списка доступных модулей"""
        modules = []
        source_dir = os.path.join(os.path.dirname(SCRIPT_DIR), "CodeNasos")
        
        if not os.path.exists(source_dir):
            print(f"{RED}❌ Папка с модулями не найдена: {source_dir}{NC}")
            sys.exit(1)

        for file in os.listdir(source_dir):
            if file.endswith('.rsc'):
                file_path = os.path.join(source_dir, file)
                size_kb = os.path.getsize(file_path) / 1024
                modules.append({
                    'name': file,
                    'path': file_path,
                    'size': size_kb
                })
        
        return sorted(modules, key=lambda x: x['name'])
    
    def display_modules(self, modules: List[Dict]):
        """Отображение списка модулей"""
        print(f"{Colors.CYAN}📋 Доступные модули:{Colors.END}")
        print(f"{'№':>3} {'Модуль':<35} {'Размер':>10}")
        print("-" * 50)
        
        for i, module in enumerate(modules, 1):
            print(f"{i:>3} {module['name']:<35} {module['size']:>10}")
    
    def select_modules(self, modules: List[Dict]) -> List[Dict]:
        """Выбор модулей для загрузки"""
        print(f"\n{Colors.YELLOW}Выберите модули для загрузки:{Colors.END}")
        print("- Введите номера через пробел (например: 1 3 5)")
        print("- Введите 'all' для всех модулей")
        print("- Введите 'q' для выхода")
        
        while True:
            choice = input("\nВаш выбор: ").strip().lower()
            
            if choice == 'q':
                sys.exit(0)
            elif choice == 'all':
                return modules
            else:
                try:
                    indices = [int(x) - 1 for x in choice.split()]
                    selected = [modules[i] for i in indices if 0 <= i < len(modules)]
                    return selected
                except (ValueError, IndexError):
                    print(f"{RED}❌ Неверный выбор. Попробуйте снова.{NC}")
    
    def upload_modules(self, modules: List[Dict]):
        """Загрузка выбранных модулей"""
        if not modules:
            print(f"{YELLOW}⚠️ Модули не выбраны{NC}")
            return
        
        print(f"\n{Colors.BLUE}🚀 Начинаю загрузку {len(modules)} модулей...{NC}")
        
        success_count = 0
        fail_count = 0
        
        for i, module in enumerate(modules, 1):
            script_name = module['name'].replace('.rsc', '')
            print(f"\n[{i}/{len(modules)}] {Colors.CYAN}📤 Загружаю {module['name']}...{NC}")
            
            if self.create_script_from_file(script_name, module['path']):
                print(f"{GREEN}✅ {module['name']} загружен успешно{NC}")
                success_count += 1
            else:
                print(f"{RED}❌ Ошибка загрузки {module['name']}{NC}")
                fail_count += 1
            
            # Небольшая пауза между загрузками
            time.sleep(0.5)
        
        print(f"\n{Colors.BOLD}📊 Результат загрузки:{NC}")
        print(f"{GREEN}✅ Успешно загружено: {success_count}{NC}")
        if fail_count > 0:
            print(f"{RED}❌ Ошибок: {fail_count}{NC}")
        
        return success_count, fail_count
    
    def list_remote_scripts(self):
        """Получение списка скриптов из RouterOS"""
        if input(f"\n{Colors.YELLOW}Показать список скриптов в RouterOS? (Y/n): {NC}").lower() != 'n':
            print(f"\n{Colors.BLUE}📋 Получаю список скриптов из RouterOS...{NC}")
            try:
                success, result = self.execute_command('/system script print brief')
                
                if success:
                    print(f"\n{Colors.CYAN}Скрипты в RouterOS:{NC}")
                    print(result)
                else:
                    print(f"{RED}❌ Не удалось получить список скриптов{NC}")
            except Exception as e:
                print(f"{RED}❌ Ошибка получения списка скриптов: {str(e)}{NC}")
    
    def run_interactive(self):
        """Интерактивный режим"""
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("=" * 60)
        print("🤖 MikroTik Module Uploader")
        print("   Автоматическая загрузка модулей RouterOS")
        print("=" * 60)
        print(f"{Colors.END}")
        
        # Настройка подключения
        self.setup_connection()
        
        # Подключение
        if not self.connect():
            return 1
        
        try:
            while True:
                modules = self.get_available_modules()
                if not modules:
                    print(f"{RED}❌ Модули не найдены в папке {self.config['source_dir']}{NC}")
                    break
                
                choice = self.select_modules(modules)
                
                # Загрузка модулей
                success_count, fail_count = self.upload_modules(choice)
                
                # Показать скрипты
                if success_count > 0:
                    try:
                        self.list_remote_scripts()
                    except (EOFError, KeyboardInterrupt):
                        break
                
                # Продолжить?
                try:
                    continue_upload = input(f"\n{Colors.YELLOW}Загрузить еще модули? (y/N): {NC}").strip()
                    if continue_upload.lower() != 'y':
                        break
                except (EOFError, KeyboardInterrupt):
                    break
                    
        finally:
            self.disconnect()
        
        print(f"\n{GREEN}🎉 Работа завершена!{NC}")
        return 0

def main():
    parser = argparse.ArgumentParser(
        description='MikroTik Module Uploader - загрузка модулей RouterOS через SSH',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--config', '-c', 
                       default='mikrotik_config.json',
                       help='Файл конфигурации (по умолчанию: mikrotik_config.json)')
    
    parser.add_argument('--batch', '-b',
                       action='store_true',
                       help='Batch режим - загрузить все модули без интерактивного меню')
    
    parser.add_argument('--list-scripts', '-l',
                       action='store_true', 
                       help='Показать список скриптов в RouterOS')
    
    args = parser.parse_args()
    
    uploader = MikroTikUploader()
    
    if args.batch:
        # Batch режим
        if not uploader.connect():
            return 1
        
        try:
            modules = uploader.get_available_modules()
            success_count, fail_count = uploader.upload_modules(modules)
            
            if args.list_scripts and success_count > 0:
                uploader.list_remote_scripts()
                
        finally:
            uploader.disconnect()
        
        return 0 if fail_count == 0 else 1
    
    elif args.list_scripts:
        # Только показать скрипты
        if not uploader.connect():
            return 1
        
        try:
            uploader.list_remote_scripts()
        finally:
            uploader.disconnect()
        
        return 0
    
    else:
        # Интерактивный режим
        return uploader.run_interactive()

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}⏹️ Прервано пользователем{NC}")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}❌ Критическая ошибка: {e}{NC}")
        sys.exit(1) 