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

class Colors:
    """ANSI цвета для консоли"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class MikroTikUploader:
    def __init__(self, config_file='mikrotik_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.ssh_client = None
        self.sftp_client = None
        
    def load_config(self):
        """Загружает конфигурацию из файла"""
        default_config = {
            "router_ip": "",
            "username": "admin",
            "password": "",
            "port": 22,
            "source_dir": "CodeNasos",  # Будет искать относительно текущей директории
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
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return {**default_config, **json.load(f)}
            except Exception as e:
                print(f"{Colors.YELLOW}⚠️ Ошибка чтения конфига: {e}{Colors.END}")
                return default_config
        else:
            return default_config
    
    def save_config(self):
        """Сохраняет конфигурацию в файл"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"{Colors.RED}❌ Ошибка сохранения конфига: {e}{Colors.END}")
    
    def setup_connection(self):
        """Настройка параметров подключения"""
        print(f"{Colors.CYAN}🔧 Настройка подключения к MikroTik{Colors.END}")
        
        try:
            # IP адрес роутера
            if not self.config["router_ip"]:
                self.config["router_ip"] = input("Введите IP адрес MikroTik роутера: ").strip()
            else:
                new_ip = input(f"IP адрес [{self.config['router_ip']}]: ").strip()
                if new_ip:
                    self.config["router_ip"] = new_ip
            
            # Имя пользователя  
            new_username = input(f"Имя пользователя [{self.config['username']}]: ").strip()
            if new_username:
                self.config["username"] = new_username
            
            # Пароль
            if not self.config["password"]:
                self.config["password"] = getpass.getpass("Введите пароль: ")
            else:
                if input("Изменить сохраненный пароль? (y/N): ").lower() == 'y':
                    self.config["password"] = getpass.getpass("Новый пароль: ")
            
            # Порт SSH
            new_port = input(f"Порт SSH [{self.config['port']}]: ").strip()
            if new_port:
                try:
                    self.config["port"] = int(new_port)
                except ValueError:
                    print(f"{Colors.YELLOW}⚠️ Неверный порт, используется {self.config['port']}{Colors.END}")
            
            self.save_config()
            print(f"{Colors.GREEN}✅ Настройки сохранены{Colors.END}")
            
        except EOFError:
            print(f"\n{Colors.YELLOW}⏹️ Прервано пользователем{Colors.END}")
            sys.exit(0)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}⏹️ Прервано пользователем{Colors.END}")
            sys.exit(0)
    
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
            print(f"{Colors.RED}❌ Ошибка подключения: {e}{Colors.END}")
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
            print(f"{Colors.YELLOW}⚠️ Ошибка при отключении: {e}{Colors.END}")
    
    def execute_command(self, command):
        """Выполнение команды на MikroTik"""
        try:
            if not self.ssh_client or not self.ssh_client.get_transport() or not self.ssh_client.get_transport().is_active():
                print(f"{Colors.YELLOW}⚠️ Переподключение к MikroTik...{Colors.END}")
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
                print(f"{Colors.RED}❌ Ошибка выполнения команды: {error}{Colors.END}")
                return False, error
            
            return True, result
            
        except Exception as e:
            print(f"{Colors.RED}❌ Ошибка SSH команды: {e}{Colors.END}")
            self.disconnect()  # Закрываем соединение при ошибке
            return False, str(e)
    
    def upload_file(self, local_path, remote_path):
        """Загрузка файла через SFTP"""
        try:
            self.sftp_client.put(local_path, remote_path)
            return True
        except Exception as e:
            print(f"{Colors.RED}❌ Ошибка загрузки файла: {e}{Colors.END}")
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
            print(f"{Colors.RED}❌ Ошибка создания скрипта: {e}{Colors.END}")
            return False
    
    def get_available_modules(self):
        """Получение списка доступных модулей"""
        source_dir = Path(self.config['source_dir'])
        if not source_dir.exists():
            print(f"{Colors.RED}❌ Папка {source_dir} не найдена{Colors.END}")
            return []
        
        modules = []
        for file_path in source_dir.glob('Nasos-*.rsc'):
            file_size = file_path.stat().st_size
            modules.append({
                'name': file_path.name,
                'path': str(file_path),
                'size': file_size,
                'size_kb': f"{file_size/1024:.1f} KB"
            })
        
        return sorted(modules, key=lambda x: x['name'])
    
    def show_modules_menu(self, modules):
        """Показать меню выбора модулей"""
        print(f"\n{Colors.CYAN}📋 Доступные модули:{Colors.END}")
        print(f"{'№':>3} {'Модуль':<35} {'Размер':>10}")
        print("-" * 50)
        
        for i, module in enumerate(modules, 1):
            print(f"{i:>3} {module['name']:<35} {module['size_kb']:>10}")
        
        print(f"\n{Colors.YELLOW}Выберите модули для загрузки:{Colors.END}")
        print("- Введите номера через пробел (например: 1 3 5)")
        print("- Введите 'all' для всех модулей")
        print("- Введите 'q' для выхода")
        
        try:
            return input("\nВаш выбор: ").strip()
        except (EOFError, KeyboardInterrupt):
            return "q"
    
    def upload_selected_modules(self, selected_modules):
        """Загрузка выбранных модулей"""
        if not selected_modules:
            print(f"{Colors.YELLOW}⚠️ Модули не выбраны{Colors.END}")
            return
        
        print(f"\n{Colors.BLUE}🚀 Начинаю загрузку {len(selected_modules)} модулей...{Colors.END}")
        
        success_count = 0
        fail_count = 0
        
        for i, module in enumerate(selected_modules, 1):
            script_name = module['name'].replace('.rsc', '')
            print(f"\n[{i}/{len(selected_modules)}] {Colors.CYAN}📤 Загружаю {module['name']}...{Colors.END}")
            
            if self.create_script_from_file(script_name, module['path']):
                print(f"{Colors.GREEN}✅ {module['name']} загружен успешно{Colors.END}")
                success_count += 1
            else:
                print(f"{Colors.RED}❌ Ошибка загрузки {module['name']}{Colors.END}")
                fail_count += 1
            
            # Небольшая пауза между загрузками
            time.sleep(0.5)
        
        print(f"\n{Colors.BOLD}📊 Результат загрузки:{Colors.END}")
        print(f"{Colors.GREEN}✅ Успешно загружено: {success_count}{Colors.END}")
        if fail_count > 0:
            print(f"{Colors.RED}❌ Ошибок: {fail_count}{Colors.END}")
        
        return success_count, fail_count
    
    def list_scripts(self):
        """Показать список скриптов в RouterOS"""
        print(f"\n{Colors.BLUE}📋 Получаю список скриптов из RouterOS...{Colors.END}")
        success, result = self.execute_command('/system script print brief')
        
        if success:
            print(f"\n{Colors.CYAN}Скрипты в RouterOS:{Colors.END}")
            print(result)
        else:
            print(f"{Colors.RED}❌ Не удалось получить список скриптов{Colors.END}")
    
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
                    print(f"{Colors.RED}❌ Модули не найдены в папке {self.config['source_dir']}{Colors.END}")
                    break
                
                choice = self.show_modules_menu(modules)
                
                if choice.lower() == 'q':
                    break
                elif choice.lower() == 'all':
                    selected_modules = modules
                else:
                    try:
                        indices = [int(x) - 1 for x in choice.split()]
                        selected_modules = [modules[i] for i in indices if 0 <= i < len(modules)]
                    except (ValueError, IndexError):
                        print(f"{Colors.RED}❌ Неверный выбор{Colors.END}")
                        continue
                
                # Загрузка модулей
                success_count, fail_count = self.upload_selected_modules(selected_modules)
                
                # Показать скрипты
                if success_count > 0:
                    try:
                        show_scripts = input(f"\n{Colors.YELLOW}Показать список скриптов в RouterOS? (Y/n): {Colors.END}").strip()
                        if show_scripts.lower() != 'n':
                            self.list_scripts()
                    except (EOFError, KeyboardInterrupt):
                        break
                
                # Продолжить?
                try:
                    continue_upload = input(f"\n{Colors.YELLOW}Загрузить еще модули? (y/N): {Colors.END}").strip()
                    if continue_upload.lower() != 'y':
                        break
                except (EOFError, KeyboardInterrupt):
                    break
                    
        finally:
            self.disconnect()
        
        print(f"\n{Colors.GREEN}🎉 Работа завершена!{Colors.END}")
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
    
    uploader = MikroTikUploader(args.config)
    
    if args.batch:
        # Batch режим
        if not uploader.connect():
            return 1
        
        try:
            modules = uploader.get_available_modules()
            success_count, fail_count = uploader.upload_selected_modules(modules)
            
            if args.list_scripts and success_count > 0:
                uploader.list_scripts()
                
        finally:
            uploader.disconnect()
        
        return 0 if fail_count == 0 else 1
    
    elif args.list_scripts:
        # Только показать скрипты
        if not uploader.connect():
            return 1
        
        try:
            uploader.list_scripts()
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
        print(f"\n{Colors.YELLOW}⏹️ Прервано пользователем{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}❌ Критическая ошибка: {e}{Colors.END}")
        sys.exit(1) 