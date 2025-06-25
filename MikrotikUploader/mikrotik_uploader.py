#!/usr/bin/env python3
import socket
import os
import codecs
import time
import glob
import sys
import re

class MikrotikUploader:
    def __init__(self):
        self.router_ip = "10.10.22.1"
        self.username = "FokinSA"
        self.password = "gjhfvtyznm"
        self.port = 8728
        self.uploaded_count = 0
        self.failed_count = 0
        
    def connect(self):
        print(f"🔗 Подключение к {self.router_ip}...")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(60)
        self.sock.connect((self.router_ip, self.port))
        
    def write_word(self, word):
        if isinstance(word, bytes):
            data = word
        else:
            # Очищаем строку от не-ASCII символов
            word = re.sub(r'[^\x00-\x7F]+', '', word)
            data = word.encode("ascii", errors="ignore")
                
        length = len(data)
        if length < 0x80:
            self.sock.send(length.to_bytes(1, byteorder='big'))
        elif length < 0x4000:
            self.sock.send(((length | 0x8000) & 0xFFFF).to_bytes(2, byteorder='big'))
        self.sock.send(data)
        
    def write_sentence(self, words):
        for word in words:
            self.write_word(word)
        self.write_word('')
        
    def read_word(self):
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
        ret = []
        while True:
            word = self.read_word()
            if not word:
                break
            ret.append(word)
        return ret
        
    def login(self):
        print("🔑 Вход...")
        self.write_sentence(['/login'])
        self.read_sentence()
        self.write_sentence(['/login', f'=name={self.username}', f'=password={self.password}'])
        reply = self.read_sentence()
        if reply[0] == '!done':
            print("✓ Вход выполнен")
            return True
        else:
            print(f"❌ Ошибка входа: {reply}")
            return False

    def verify_script_exists(self, script_name):
        """Проверка существования скрипта"""
        self.write_sentence(['/system/script/print', f'?name={script_name}'])
        exists = False
        while True:
            reply = self.read_sentence()
            if not reply:
                break
            if reply[0] == '!re':
                for word in reply:
                    if word.startswith('=name=') and word[6:] == script_name:
                        exists = True
                        break
            elif reply[0] == '!done':
                break
        return exists

    def verify_scheduler_exists(self, scheduler_name):
        """Проверка существования шедулера"""
        self.write_sentence(['/system/scheduler/print', f'?name={scheduler_name}'])
        exists = False
        while True:
            reply = self.read_sentence()
            if not reply:
                break
            if reply[0] == '!re':
                for word in reply:
                    if word.startswith('=name=') and word[6:] == scheduler_name:
                        exists = True
                        break
            elif reply[0] == '!done':
                break
        return exists

    def remove_script(self, script_name):
        """Удаление скрипта с проверкой"""
        # Проверяем существование скрипта
        self.write_sentence(['/system/script/print', f'?name={script_name}'])
        script_id = None
        while True:
            reply = self.read_sentence()
            if not reply:
                break
            if reply[0] == '!re':
                for word in reply:
                    if word.startswith('=.id='):
                        script_id = word[5:]
                        break
            elif reply[0] == '!done':
                break
        
        if script_id:
            # Удаляем скрипт
            self.write_sentence(['/system/script/remove', f'=.id={script_id}'])
            while True:
                reply = self.read_sentence()
                if not reply or reply[0] == '!done':
                    break
            time.sleep(1)
            
            # Проверяем что скрипт действительно удален
            if self.verify_script_exists(script_name):
                print(f"❌ Ошибка: скрипт {script_name} не был удален")
                return False
            return True
        return True  # Скрипт не существует - значит уже удален

    def remove_scheduler(self, scheduler_name):
        """Удаление шедулера с проверкой"""
        if self.verify_scheduler_exists(scheduler_name):
            self.write_sentence(['/system/scheduler/remove', f'=.id=[find name={scheduler_name}]'])
            reply = self.read_sentence()
            time.sleep(1)
            if self.verify_scheduler_exists(scheduler_name):
                print(f"❌ Ошибка: шедулер {scheduler_name} не был удален")
                return False
        return True

    def get_mikrotik_time(self):
        """Получение текущего времени микротика"""
        self.write_sentence(['/system/clock/print'])
        clock_data = self.read_sentence()
        
        for line in clock_data:
            if line.startswith('=time='):
                time_str = line[6:]
                try:
                    h, m, s = map(int, time_str.split(':'))
                    # Добавляем 5 секунд
                    s += 5
                    if s >= 60:
                        s -= 60
                        m += 1
                        if m >= 60:
                            m -= 60
                            h += 1
                            if h >= 24:
                                h -= 24
                    return f"{h:02d}:{m:02d}:{s:02d}"
                except ValueError:
                    break
        return None
    
    def upload_script(self, script_name, content):
        """Загрузка скрипта с проверкой"""
        # Для больших файлов используем специальный метод
        if len(content) > 15000 and not script_name.endswith(('-TEMP1', '-TEMP2', '-Combine')):
            return self.upload_large_script(script_name, content)
        
        sock = None
        try:
            print(f"\n📤 {script_name} ({len(content)} байт)...")
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(60)
            sock.connect((self.router_ip, self.port))
            self.sock = sock
            
            if not self.login():
                return False
    
            time.sleep(2)
            
            # Удаление старого скрипта если есть
            if not self.remove_script(script_name):
                return False
            
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Загрузка
            self.write_sentence([
                '/system/script/add',
                f'=name={script_name}',
                f'=source={content}',
                '=policy=read,write,policy,test'
            ])
            
            # Читаем все ответы до !done
            success = False
            while True:
                reply = self.read_sentence()
                if not reply:
                    break
                if reply[0] == '!done':
                    success = True
                    break
                elif reply[0] == '!trap':
                    print(f"❌ Ошибка: {reply}")
                    return False
            
            if success:
                # Проверяем что скрипт действительно создан
                if self.verify_script_exists(script_name):
                    print(f"✅ {script_name} загружен")
                    self.uploaded_count += 1
                    return True
                else:
                    print(f"❌ Ошибка: скрипт {script_name} не найден после загрузки")
                    self.failed_count += 1
                    return False
            else:
                print(f"❌ Ошибка {script_name}: не получен ответ !done")
                self.failed_count += 1
                return False
            
        except Exception as e:
            print(f"❌ Ошибка {script_name}: {e}")
            self.failed_count += 1
            return False
        finally:
            if sock:
                sock.close()
            time.sleep(3)

    def upload_large_script(self, script_name, content):
        """Загрузка большого скрипта по частям с последующим объединением через шедулер"""
        print(f"\n📦 Загрузка большого скрипта {script_name} ({len(content)} байт)")
        
        try:
            # Создаем новое подключение для всей операции
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(60)
            sock.connect((self.router_ip, self.port))
            self.sock = sock
            
            if not self.login():
                return False
            
            # Разделяем на части по 15KB
            parts = []
            chunk_size = 15000
            for i in range(0, len(content), chunk_size):
                parts.append(content[i:i + chunk_size])
            
            print(f"📑 Разделено на {len(parts)} части")
            
            # Загружаем временные части
            for i, part in enumerate(parts, 1):
                temp_name = f"{script_name}-TEMP{i}"
                print(f"\n📤 Загрузка части {i}/{len(parts)}: {temp_name}")
                
                # Удаляем старый временный скрипт если есть
                if not self.remove_script(temp_name):
                    raise Exception(f"Не удалось удалить старый временный скрипт {temp_name}")
                
                # Загрузка части
                self.write_sentence([
                    '/system/script/add',
                    f'=name={temp_name}',
                    f'=source={part}',
                    '=policy=read,write,policy,test'
                ])
                
                # Читаем все ответы до !done
                success = False
                while True:
                    reply = self.read_sentence()
                    if not reply:
                        break
                    if reply[0] == '!done':
                        success = True
                        break
                    elif reply[0] == '!trap':
                        raise Exception(f"Ошибка загрузки части {i}: {reply}")
                
                if not success:
                    raise Exception(f"Не получен ответ !done для части {i}")
                
                # Проверяем что часть действительно создана
                if not self.verify_script_exists(temp_name):
                    raise Exception(f"Часть {temp_name} не найдена после загрузки")
                
                print(f"✅ {temp_name} загружен")
                time.sleep(2)
                
            # Создаем объединяющий скрипт
            print("\n🔄 Объединение частей...")
            combine_script = f"""
# Объединяем части скрипта {script_name}
:local content ""

# Читаем части
"""
            
            # Добавляем код для каждой части
            for i in range(1, len(parts) + 1):
                combine_script += f"""
:local part{i} [/system script get {script_name}-TEMP{i} source]
:set content ($content . $part{i})
"""
            
            # Добавляем создание финального скрипта и очистку
            combine_script += f"""
# Создаем финальный скрипт
/system script add name="{script_name}" source=$content policy=read,write,policy,test

# Удаляем временные части
"""
            
            # Добавляем удаление всех временных частей
            for i in range(1, len(parts) + 1):
                combine_script += f'/system script remove [find name="{script_name}-TEMP{i}"]\n'
            
            # Выводим содержимое для отладки
            print("\n📝 Содержимое combine скрипта:")
            print(combine_script)
            
            # Загружаем объединяющий скрипт
            combine_name = f"{script_name}-Combine"
            print(f"📤 Загрузка объединяющего скрипта {combine_name}")
            
            # Удаляем старый combine скрипт если есть
            if not self.remove_script(combine_name):
                raise Exception(f"Не удалось удалить старый скрипт {combine_name}")
            
            # Загрузка combine скрипта
            self.write_sentence([
                '/system/script/add',
                f'=name={combine_name}',
                f'=source={combine_script}',
                '=policy=read,write,policy,test'
            ])
            
            # Читаем все ответы до !done
            success = False
            while True:
                reply = self.read_sentence()
                if not reply:
                    break
                if reply[0] == '!done':
                    success = True
                    break
                elif reply[0] == '!trap':
                    raise Exception(f"Ошибка загрузки объединяющего скрипта: {reply}")
            
            if not success:
                raise Exception("Не получен ответ !done для объединяющего скрипта")
            
            # Проверяем что combine скрипт создан
            if not self.verify_script_exists(combine_name):
                raise Exception(f"Скрипт {combine_name} не найден после загрузки")
            
            print(f"✅ {combine_name} загружен")
            
            # Получаем время микротика для шедулера
            start_time = self.get_mikrotik_time()
            if not start_time:
                raise Exception("Не удалось получить время микротика")
            
            # Создаем шедулер для запуска combine скрипта
            scheduler_name = f"run-{script_name}-combine"
            print(f"⏰ Создание шедулера {scheduler_name} на {start_time}...")
            
            # Удаляем старый шедулер если есть
            if not self.remove_scheduler(scheduler_name):
                raise Exception(f"Не удалось удалить старый шедулер {scheduler_name}")
            
            # Создаем новый шедулер
            self.write_sentence([
                '/system/scheduler/add',
                f'=name={scheduler_name}',
                f'=on-event=/system script run {script_name}-Combine; :delay 2s; /system script remove {script_name}-Combine; /system scheduler remove {scheduler_name}',
                f'=start-time={start_time}',
                '=interval=0s',
                '=policy=read,write,policy,test'
            ])
            
            # Читаем ответ
            success = False
            while True:
                reply = self.read_sentence()
                if not reply:
                    break
                if reply[0] == '!done':
                    success = True
                    break
                elif reply[0] == '!trap':
                    raise Exception(f"Ошибка создания шедулера: {reply}")
            
            if not success:
                raise Exception("Не получен ответ !done при создании шедулера")
            
            print(f"⏳ Ожидание выполнения объединения...")
            time.sleep(30)  # Увеличиваем время ожидания до 30 секунд
            
            # Проверяем что финальный скрипт создан
            if not self.verify_script_exists(script_name):
                raise Exception(f"Финальный скрипт {script_name} не найден после объединения")
            
            print(f"✅ Скрипт {script_name} успешно собран!")
            self.uploaded_count += 1
            return True
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            self.failed_count += 1
            return False
        finally:
            if 'sock' in locals():
                sock.close()
            time.sleep(3)
    
    def list_scripts(self):
        """Показать загруженные скрипты."""
        try:
            self.connect()
            if not self.login():
                return
        
            self.write_sentence(['/system/script/print'])
            
            nasos_scripts = []
            while True:
                reply = self.read_sentence()
                if not reply or reply[0] == '!done':
                    break
                
                if reply[0] == '!re':
                    for item in reply:
                        if item.startswith('=name='):
                            script_name = item[6:]
                            if script_name.startswith('Nasos-'):
                                nasos_scripts.append(script_name)
            
            print(f"\n📋 Загружено Nasos скриптов: {len(nasos_scripts)}")
            for script in sorted(nasos_scripts):
                print(f"  • {script}")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        finally:
            self.sock.close()

    def upload_modules(self, module_names=None):
        """Загрузка модулей."""
        script_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CodeNasos')
        
        if module_names is None:
            # Все .rsc файлы
            rsc_files = glob.glob(os.path.join(script_dir, '*.rsc'))
        else:
            # Конкретные модули
            rsc_files = []
            for name in module_names:
                if not name.endswith('.rsc'):
                    name += '.rsc'
                file_path = os.path.join(script_dir, name)
                if os.path.exists(file_path):
                    rsc_files.append(file_path)
                else:
                    print(f"❌ Файл {name} не найден")
        
        if not rsc_files:
            print("❌ Нет файлов для загрузки")
            return
            
        print(f"📋 К загрузке: {len(rsc_files)} модулей")
        
        self.uploaded_count = 0
        self.failed_count = 0
        
        for i, file_path in enumerate(sorted(rsc_files), 1):
            try:
                filename = os.path.basename(file_path)
                script_name = filename.replace('.rsc', '')
                
                print(f"[{i}/{len(rsc_files)}] {filename}")
                
                try:
                    with codecs.open(file_path, 'r', encoding='utf-8-sig') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with codecs.open(file_path, 'r', encoding='windows-1251') as f:
                        content = f.read()
                
                self.upload_script(script_name, content)
                
            except Exception as e:
                print(f"❌ Ошибка {filename}: {e}")
                self.failed_count += 1
        
        print(f"\n📊 Загружено: {self.uploaded_count}, Ошибок: {self.failed_count}")

def main():
    uploader = MikrotikUploader()
    
    if len(sys.argv) == 1:
        # Без параметров - загрузить все
        print("🎯 Загрузка всех модулей NasosRunner")
        uploader.upload_modules()
    elif sys.argv[1] == 'list':
        # Показать загруженные
            uploader.list_scripts()
    else:
        # Загрузить конкретные модули
        modules = sys.argv[1:]
        print(f"🎯 Загрузка модулей: {', '.join(modules)}")
        uploader.upload_modules(modules)

if __name__ == '__main__':
    main()
