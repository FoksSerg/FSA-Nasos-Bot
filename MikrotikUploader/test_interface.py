#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование интерфейса MikroTik Uploader без подключения к роутеру
"""

import sys
from mikrotik_uploader import MikroTikUploader, Colors

class TestMikroTikUploader(MikroTikUploader):
    """Тестовая версия загрузчика без реального подключения"""
    
    def connect(self):
        """Имитация успешного подключения"""
        print(f"{Colors.BLUE}🔗 [ТЕСТ] Имитация подключения к {self.config['router_ip']}:{self.config['port']}...{Colors.END}")
        print(f"{Colors.GREEN}✅ [ТЕСТ] Подключение установлено (имитация){Colors.END}")
        return True
    
    def disconnect(self):
        """Имитация отключения"""
        print(f"{Colors.BLUE}🔌 [ТЕСТ] Отключено от MikroTik (имитация){Colors.END}")
    
    def create_script_from_file(self, script_name, local_file_path):
        """Имитация создания скрипта"""
        print(f"{Colors.CYAN}📝 [ТЕСТ] Имитирую создание скрипта: {script_name}{Colors.END}")
        # Имитируем время загрузки
        import time
        time.sleep(0.2)
        return True
    
    def list_scripts(self):
        """Имитация списка скриптов"""
        print(f"\n{Colors.BLUE}📋 [ТЕСТ] Получаю список скриптов из RouterOS...{Colors.END}")
        
        fake_scripts = """Flags: I - invalid, D - disabled 
 #    NAME                     OWNER                   LAST-STARTED             
 0    Nasos-Runner            admin                   Jan/01/1970 00:00:00    
 1    Nasos-Telegram          admin                   Jan/01/1970 00:00:00    
 2    Nasos-Messages          admin                   Jan/01/1970 00:00:00    
 3    Nasos-TG-Activator      admin                   Jan/01/1970 00:00:00    
 4    Nasos-TG-Poller         admin                   Jan/01/1970 00:00:00    
 5    Nasos-Startup           admin                   Jan/01/1970 00:00:00"""
        
        print(f"\n{Colors.CYAN}[ТЕСТ] Скрипты в RouterOS:{Colors.END}")
        print(fake_scripts)

def main():
    print(f"{Colors.BOLD}{Colors.PURPLE}")
    print("=" * 70)
    print("🧪 ТЕСТОВЫЙ РЕЖИМ - MikroTik Module Uploader")
    print("   Проверка интерфейса без реального подключения")
    print("=" * 70)
    print(f"{Colors.END}")
    
    # Создаем тестовый экземпляр
    uploader = TestMikroTikUploader("test_config.json")
    
    # Запускаем интерактивный режим
    return uploader.run_interactive()

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⏹️ Тест прерван пользователем{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}❌ Ошибка в тесте: {e}{Colors.END}")
        sys.exit(1) 