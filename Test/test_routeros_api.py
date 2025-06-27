#!/usr/bin/env python3
"""
Тестирование различных RouterOS API запросов для получения списка скриптов
"""

import socket
import time

class MikrotikTester:
    def __init__(self, router_ip, username, password, port=8728):
        self.router_ip = router_ip
        self.username = username
        self.password = password
        self.port = port
        self.sock = None
        
    def connect(self):
        """Подключение к роутеру"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(60)
        self.sock.connect((self.router_ip, self.port))
        
    def close(self):
        """Закрытие соединения"""
        if self.sock:
            self.sock.close()
            
    def write_word(self, word):
        """Отправка одного слова (копия из MikrotikUploader)"""
        if isinstance(word, bytes):
            data = word
        else:
            data = word.encode("ascii", errors="ignore")
                
        length = len(data)
        
        if length < 0x80:
            self.sock.send(length.to_bytes(1, byteorder='big'))
        elif length < 0x4000:
            self.sock.send(((length | 0x8000) & 0xFFFF).to_bytes(2, byteorder='big'))
        
        self.sock.send(data)
        
    def write_sentence(self, words):
        """Отправка предложения (копия из MikrotikUploader)"""
        for word in words:
            self.write_word(word)
        self.write_word("")  # Пустое слово - маркер конца
        
    def read_word(self):
        """Чтение одного слова (копия из MikrotikUploader)"""
        ret = b''
        
        length = int.from_bytes(self.sock.recv(1), byteorder='big')
        
        if length & 0x80:
            length = ((length & 0x7F) << 8) | int.from_bytes(self.sock.recv(1), byteorder='big')
        
        while length > 0:
            t = self.sock.recv(length)
            ret += t
            length -= len(t)
        
        try:
            return ret.decode("ascii", errors="ignore")
        except UnicodeDecodeError:
            return ret.decode('utf-8', errors='replace')
        
    def read_sentence(self):
        """Чтение предложения (копия из MikrotikUploader)"""
        ret = []
        
        while True:
            word = self.read_word()
            if not word:
                break
            ret.append(word)
            
        return ret
        
    def login(self):
        """Авторизация (копия из MikrotikUploader)"""
        print("🔑 Авторизация...")
        
        # Шаг 1: Инициация авторизации
        self.write_sentence(['/login'])
        self.read_sentence()
        
        # Шаг 2: Отправка данных авторизации
        self.write_sentence(['/login', f'=name={self.username}', f'=password={self.password}'])
        reply = self.read_sentence()
        
        if reply[0] == '!done':
            print("✅ Авторизация успешна")
            return True
        else:
            print(f"❌ Ошибка авторизации: {reply}")
            return False
            
    def test_script_id_requests(self):
        """Тестирование получения ID скриптов для удаления"""
        
        print("\n" + "="*80)
        print("🆔 ТЕСТИРОВАНИЕ ПОЛУЧЕНИЯ ID СКРИПТОВ")
        print("="*80)
        
        # Сначала получим список всех скриптов с простым запросом
        print("\n🔍 Получение списка скриптов для тестирования...")
        self.write_sentence(['/system/script/print', '=.proplist=name'])
        
        available_scripts = []
        while True:
            reply = self.read_sentence()
            if not reply:
                break
            if reply[0] == '!re':
                for item in reply[1:]:
                    if item.startswith('=name='):
                        available_scripts.append(item[6:])
            elif reply[0] == '!done':
                break
        
        print(f"📋 Найдено скриптов: {len(available_scripts)}")
        for i, script in enumerate(available_scripts[:5], 1):  # Показываем только первые 5
            print(f"   {i}. {script}")
        
        if not available_scripts:
            print("❌ Нет скриптов для тестирования")
            return
            
        # Берем первые несколько скриптов для тестирования ID
        test_scripts = available_scripts[:3]
        
        id_requests = [
            {
                "name": "ID тест 1: Полный запрос (с source)",
                "command": ['/system/script/print'],
                "description": "Может вызвать пагинацию для больших скриптов"
            },
            {
                "name": "ID тест 2: Только ID и name",  
                "command": ['/system/script/print', '=.proplist=.id,name'],
                "description": "Безопасный запрос без source"
            },
            {
                "name": "ID тест 3: Поиск конкретного скрипта",
                "command": ['/system/script/print', f'?name={test_scripts[0]}', '=.proplist=.id,name'],
                "description": f"Поиск ID для скрипта '{test_scripts[0]}'"
            }
        ]
        
        for test in id_requests:
            print("\n" + "-"*60)
            print(f"🧪 {test['name']}")
            print(f"💡 {test['description']}")
            print("-"*60)
            
            try:
                print(f"📤 Запрос: {test['command']}")
                self.write_sentence(test['command'])
                
                scripts_found = 0
                scripts_with_id = 0
                
                while True:
                    reply = self.read_sentence()
                    if not reply:
                        break
                        
                    if reply[0] == '!re':
                        scripts_found += 1
                        
                        script_name = "неизвестно"
                        script_id = None
                        script_source_len = 0
                        
                        for item in reply[1:]:
                            if item.startswith('=name='):
                                script_name = item[6:]
                            elif item.startswith('=.id='):
                                script_id = item[5:]
                                scripts_with_id += 1
                            elif item.startswith('=source='):
                                script_source_len = len(item[8:])
                        
                        print(f"   📜 Скрипт: {script_name}")
                        print(f"      🆔 ID: {script_id if script_id else '❌ НЕ ПОЛУЧЕН'}")
                        if script_source_len > 0:
                            print(f"      📄 Source: {script_source_len} байт")
                            
                        # Останавливаемся после первых 3 скриптов для читаемости
                        if scripts_found >= 3:
                            print(f"   ... (показаны первые 3 из возможно большего количества)")
                            # Дочитываем остальные ответы
                            while True:
                                remaining = self.read_sentence()
                                if not remaining or remaining[0] == '!done':
                                    break
                            break
                                
                    elif reply[0] == '!done':
                        print(f"✅ Завершено")
                        break
                    elif reply[0] == '!trap':
                        print(f"❌ Ошибка: {reply}")
                        break
                
                print(f"📊 Результат: {scripts_with_id}/{scripts_found} скриптов получили ID")
                        
            except Exception as e:
                print(f"❌ Исключение: {e}")
                
            time.sleep(1)

    def test_script_requests(self):
        """Тестирование различных запросов скриптов"""
        
        requests = [
            {
                "name": "Вариант 1: Простой запрос",
                "command": ['/system/script/print']
            },
            {
                "name": "Вариант 2: Без source поля",
                "command": ['/system/script/print', '=.proplist=.id,name,owner,run-count']
            },
            {
                "name": "Вариант 3: Without-paging",
                "command": ['/system/script/print', '=without-paging=']
            }
        ]
        
        for test in requests:
            print("\n" + "="*80)
            print(f"🧪 {test['name']}")
            print("="*80)
            
            try:
                # Отправляем запрос
                print(f"📤 Отправка: {test['command']}")
                self.write_sentence(test['command'])
                
                scripts_count = 0
                
                # Читаем ответы
                while True:
                    reply = self.read_sentence()
                    if not reply:
                        break
                        
                    print(f"📥 Ответ: {reply[0]}")
                    
                    if reply[0] == '!re':
                        scripts_count += 1
                        
                        # Ищем имя скрипта
                        script_name = "неизвестно"
                        script_source_len = 0
                        
                        for item in reply[1:]:
                            if item.startswith('=name='):
                                script_name = item[6:]
                            elif item.startswith('=source='):
                                script_source_len = len(item[8:])
                                
                        print(f"   📜 Скрипт #{scripts_count}: {script_name} (source: {script_source_len} байт)")
                        
                    elif reply[0] == '!done':
                        print(f"✅ Завершено. Получено скриптов: {scripts_count}")
                        break
                    elif reply[0] == '!trap':
                        print(f"❌ Ошибка: {reply}")
                        break
                        
            except Exception as e:
                print(f"❌ Исключение: {e}")
                
            time.sleep(1)  # Пауза между тестами

def test_api_variants():
    print("=" * 80)
    print("🧪 ТЕСТИРОВАНИЕ RouterOS API ЗАПРОСОВ")
    print("=" * 80)
    
    # Настройки подключения из GUI
    IP = "10.10.44.1"
    PORT = 8728
    USERNAME = "FokinSA"
    PASSWORD = "gjhfvtyznm"
    
    tester = MikrotikTester(IP, USERNAME, PASSWORD, PORT)
    
    try:
        print(f"🔗 Подключение к {IP}:{PORT}...")
        tester.connect()
        print("✅ Подключение установлено")
        
        if not tester.login():
            print("❌ Авторизация не удалась")
            return
            
        # НОВЫЕ ТЕСТЫ ID В НАЧАЛЕ
        tester.test_script_id_requests()
        
        # Существующие тесты
        tester.test_script_requests()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        print("\n🔌 Закрытие соединения...")
        tester.close()

if __name__ == "__main__":
    test_api_variants()