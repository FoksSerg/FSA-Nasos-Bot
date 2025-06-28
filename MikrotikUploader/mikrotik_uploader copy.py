#!/usr/bin/env python3
"""
MikrotikUploader GUI - Графический интерфейс для загрузки скриптов на RouterOS

Возможности:
- Управление списком роутеров (добавление, редактирование, удаление)
- Просмотр содержимого роутера (скрипты, шедулеры)
- Выбор папки с исходниками и отметка файлов для загрузки
- Контроль процесса загрузки с прогресс-баром
- Логирование всех операций в реальном времени
- Сохранение настроек между сессиями

Автор: NasosRunner Project
Версия: 1.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import threading
import queue
import codecs
import glob
from datetime import datetime
import socket   # Для TCP подключения к API
import time     # Для пауз между операциями
import sys      # Для работы с аргументами командной строки
import re       # Для регулярных выражений (очистка символов)

def find_codenosos_dir():
    """
    Универсальный поиск папки CodeNasos начиная от текущего файла и поднимаясь вверх.
    
    Алгоритм поиска:
    1. Начинаем от директории текущего файла
    2. Проверяем существование папки CodeNasos в текущей директории
    3. Если не найдена - поднимаемся на уровень выше
    4. Повторяем до корня файловой системы или пока не найдем
    
    Returns:
        str: Полный путь к папке CodeNasos
        None: Если папка не найдена
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Поднимаемся максимум на 5 уровней вверх (защита от бесконечного цикла)
    for _ in range(5):
        codenosos_path = os.path.join(current_dir, 'CodeNasos')
        if os.path.exists(codenosos_path) and os.path.isdir(codenosos_path):
            return codenosos_path
        
        # Поднимаемся на уровень выше
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:  # Достигли корня файловой системы
            break
        current_dir = parent_dir
    
    return None

class MikrotikUploader:
    """
    Класс для загрузки скриптов на Mikrotik через API протокол.
    
    Основные возможности:
    - Подключение к роутеру через API (порт 8728)
    - Авторизация пользователя
    - Загрузка скриптов с проверкой размера
    - Разделение больших скриптов на части
    - Автоматическое объединение частей через scheduler
    - Проверка успешности операций
    
    Архитектура работы с большими файлами:
    1. Файл разделяется на части по 15KB
    2. Каждая часть загружается как временный скрипт (script-TEMP1, script-TEMP2...)
    3. Создается combine-скрипт для объединения частей
    4. Через scheduler запускается combine-скрипт
    5. Combine-скрипт создает финальный скрипт и удаляет временные части
    """
    
    def __init__(self):
        """
        Инициализация параметров подключения и счетчиков.
        
        Устанавливает:
        - IP адрес роутера (можно изменить для вашего роутера)
        - Данные для авторизации (логин/пароль)
        - Порт API (8728 - стандартный порт Mikrotik API)
        - Счетчики успешных и неудачных загрузок
        """
        # Параметры подключения к роутеру Mikrotik
        self.router_ip = "10.10.55.1"        # IP адрес роутера
        self.username = "FokinSA"             # Имя пользователя для API
        self.password = "gjhfvtyznm"          # Пароль пользователя
        self.port = 8728                      # Порт API Mikrotik (стандартный)
        
        # Счетчики для отслеживания результатов загрузки
        self.uploaded_count = 0               # Количество успешно загруженных скриптов
        self.failed_count = 0                 # Количество неудачных загрузок
        
    def connect(self):
        """
        Создание TCP сокета и подключение к роутеру.
        
        Процесс подключения:
        1. Создание TCP сокета для IPv4
        2. Установка таймаута 60 секунд для предотвращения зависания
        3. Подключение к указанному IP и порту
        
        Raises:
            socket.error: При ошибке подключения к роутеру
            socket.timeout: При превышении таймаута подключения
        """
        print(f"🔗 Подключение к {self.router_ip}...")
        
        # Создаем TCP сокет для IPv4 (AF_INET) и потоковый протокол (SOCK_STREAM)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Устанавливаем таймаут 60 секунд для всех операций с сокетом
        # Это предотвращает бесконечное ожидание при потере связи
        self.sock.settimeout(60)
        
        # Подключаемся к роутеру по указанному IP и порту
        self.sock.connect((self.router_ip, self.port))
        
    def write_word(self, word):
        """
        Отправка одного "слова" через API протокол Mikrotik.
        
        Протокол кодирования длины в API Mikrotik:
        - Если длина < 128 байт (0x80): отправляется 1 байт длины
        - Если длина < 16384 байт (0x4000): отправляется 2 байта длины 
          с установленным старшим битом (0x8000)
        - Затем отправляются сами данные
        
        Обработка кодировки:
        - Удаляются все не-ASCII символы для совместимости с RouterOS
        - Используется ASCII кодировка с игнорированием ошибок
        - RouterOS API работает только с ASCII символами
        
        Args:
            word (str|bytes): Слово для отправки. Может быть строкой или байтами.
        
        Note:
            Этот метод реализует низкоуровневый протокол API Mikrotik.
            Каждое "слово" - это атомарная единица данных в протоколе.
        """
        if isinstance(word, bytes):
            # Если данные уже в байтах - используем как есть
            data = word
        else:
            # Очищаем строку от не-ASCII символов для совместимости с RouterOS
            # RouterOS API не поддерживает Unicode символы
            word = re.sub(r'[^\x00-\x7F]+', '', word)
            
            # Кодируем строку в ASCII с игнорированием ошибок
            # errors="ignore" пропускает символы, которые нельзя закодировать
            data = word.encode("ascii", errors="ignore")
                
        length = len(data)
        
        # Кодирование длины по протоколу API Mikrotik
        if length < 0x80:  # Если длина меньше 128 байт
            # Отправляем длину в одном байте (big-endian)
            self.sock.send(length.to_bytes(1, byteorder='big'))
        elif length < 0x4000:  # Если длина меньше 16384 байт
            # Устанавливаем старший бит (0x8000) и отправляем в 2 байтах
            # Формула: (длина | 0x8000) устанавливает флаг многобайтовой длины
            self.sock.send(((length | 0x8000) & 0xFFFF).to_bytes(2, byteorder='big'))
        
        # Отправляем сами данные после заголовка длины
        self.sock.send(data)
        
    def write_sentence(self, words):
        """
        Отправка "предложения" (команды) через API.
        
        Предложение в API Mikrotik - это полная команда, состоящая из:
        1. Команды (например, "/system/script/add")
        2. Параметров (например, "=name=script_name", "=source=content")
        3. Пустого слова в качестве маркера конца предложения
        
        Примеры предложений:
        - ["/login", "=name=admin", "=password=123"] - авторизация
        - ["/system/script/print"] - вывод списка скриптов
        - ["/system/script/add", "=name=test", "=source=:put hello"] - создание скрипта
        
        Args:
            words (list): Список слов (строк) для отправки как одно предложение
        
        Note:
            Каждое предложение должно заканчиваться пустым словом.
            Это сигнализирует серверу о завершении команды.
        """
        # Отправляем каждое слово в предложении
        for word in words:
            self.write_word(word)
        
        # Отправляем пустое слово как маркер конца предложения
        # Это обязательный элемент протокола API
        self.write_word('')
        
    def read_word(self):
        """
        Чтение одного "слова" из ответа роутера.
        
        Протокол декодирования длины:
        1. Читаем первый байт длины
        2. Если установлен старший бит (0x80) - читаем второй байт
        3. Вычисляем полную длину данных
        4. Читаем указанное количество байт данных
        
        Обработка кодировок:
        - Сначала пробуем декодировать как ASCII (основная кодировка API)
        - При ошибке переходим на UTF-8 с заменой некорректных символов
        - Это обеспечивает совместимость с различными версиями RouterOS
        
        Returns:
            str: Декодированное слово из ответа роутера
            
        Raises:
            socket.error: При ошибке чтения из сокета
            
        Note:
            Метод может вызываться многократно для чтения одного recv(),
            так как TCP может доставлять данные частями.
        """
        ret = b''  # Буфер для накопления байтов слова
        
        # Читаем первый байт длины (всегда присутствует)
        length = int.from_bytes(self.sock.recv(1), byteorder='big')
        
        # Проверяем старший бит для определения формата длины
        if length & 0x80:  # Если установлен бит 0x80
            # Длина кодируется в 2 байтах
            # Убираем старший бит из первого байта и объединяем со вторым
            length = ((length & 0x7F) << 8) | int.from_bytes(self.sock.recv(1), byteorder='big')
        
        # Читаем данные слова (может потребоваться несколько вызовов recv)
        while length > 0:
            t = self.sock.recv(length)  # Читаем оставшиеся байты
            ret += t                    # Добавляем к буферу
            length -= len(t)            # Уменьшаем счетчик оставшихся байт
        
        # Пробуем различные кодировки для декодирования байтов в строку
        try:
            # Сначала пробуем ASCII (основная кодировка API Mikrotik)
            return ret.decode("ascii", errors="ignore")
        except UnicodeDecodeError:
            # При ошибке используем UTF-8 с заменой некорректных символов
            # errors='replace' заменяет проблемные символы на '?'
            return ret.decode('utf-8', errors='replace')
        
    def read_sentence(self):
        """
        Чтение полного "предложения" (ответа) от роутера.
        
        Предложение читается до получения пустого слова (маркер конца).
        Возвращает список всех слов в предложении.
        
        Типы ответов RouterOS API:
        - !done - команда выполнена успешно
        - !trap - произошла ошибка при выполнении команды  
        - !re - строка данных (используется при выводе списков)
        - !fatal - критическая ошибка (разрыв соединения)
        
        Структура ответа:
        ["!done"] - простое подтверждение
        ["!re", "=name=script1", "=policy=read,write", "!done"] - данные + подтверждение
        ["!trap", "=message=syntax error"] - ошибка с описанием
        
        Returns:
            list: Список слов в предложении. Пустой список при отсутствии данных.
            
        Note:
            Метод блокирующий - ждет полного получения предложения от сервера.
        """
        ret = []  # Список для накопления слов предложения
        
        while True:
            word = self.read_word()  # Читаем очередное слово
            if not word:  # Пустое слово означает конец предложения
                break
            ret.append(word)  # Добавляем слово к результату
            
        return ret
        
    def login(self):
        """
        Авторизация на роутере через API.
        
        Процесс авторизации в API Mikrotik (упрощенный для новых версий):
        1. Отправляем команду /login для инициации процесса
        2. Читаем ответ (в старых версиях содержит challenge)
        3. Отправляем /login с именем пользователя и паролем
        4. Проверяем ответ (!done = успех, !trap = ошибка)
        
        Поддерживаемые версии:
        - RouterOS 6.43+ (упрощенная авторизация без MD5 challenge)
        - RouterOS 7.x (современный метод авторизации)
        
        Returns:
            bool: True если авторизация успешна, False при ошибке
            
        Note:
            В старых версиях RouterOS требовался MD5-хеш от пароля и challenge.
            Современные версии поддерживают прямую передачу пароля.
        """
        print("🔑 Вход...")
        
        # Шаг 1: Отправляем начальную команду авторизации
        self.write_sentence(['/login'])
        self.read_sentence()  # Читаем ответ (может содержать challenge в старых версиях)
        
        # Шаг 2: Отправляем данные авторизации
        # =name= и =password= - стандартные параметры API для авторизации
        self.write_sentence(['/login', f'=name={self.username}', f'=password={self.password}'])
        reply = self.read_sentence()
        
        # Проверяем результат авторизации по первому слову ответа
        if reply[0] == '!done':
            print("✓ Вход выполнен")
            return True
        else:
            print(f"❌ Ошибка входа: {reply}")
            return False

    def verify_script_exists(self, script_name):
        """
        Проверка существования скрипта на роутере.
        
        Использует команду /system/script/print с фильтром по имени.
        Фильтр ?name=script_name ограничивает вывод только нужным скриптом,
        что повышает производительность при большом количестве скриптов.
        
        Алгоритм проверки:
        1. Отправляем команду печати с фильтром по имени
        2. Читаем все ответы до получения !done
        3. Ищем в ответах строки с =name= и сравниваем значения
        4. Возвращаем результат проверки
        
        Args:
            script_name (str): Имя скрипта для проверки существования
            
        Returns:
            bool: True если скрипт существует на роутере, False если нет
            
        Note:
            Метод безопасен - не изменяет состояние роутера, только читает.
        """
        # Отправляем команду вывода скриптов с фильтром по имени
        # ?name=script_name - это фильтр API для ограничения результатов
        # =.proplist=.id,name - запрашиваем только ID и имя (избегаем пагинации больших скриптов)
        self.write_sentence(['/system/script/print', f'?name={script_name}', '=.proplist=.id,name'])
        
        exists = False  # Флаг существования скрипта
        
        # Читаем все ответы до завершения команды
        while True:
            reply = self.read_sentence()
            if not reply:  # Пустой ответ - завершаем чтение
                break
                
            if reply[0] == '!re':  # !re означает строку данных
                # Проверяем каждое слово в строке данных
                for word in reply:
                    # Ищем параметр имени и сравниваем значение
                    if word.startswith('=name=') and word[6:] == script_name:
                        exists = True
                        break
            elif reply[0] == '!done':  # Конец вывода команды
                break
                
        return exists

    def verify_scheduler_exists(self, scheduler_name):
        """
        Проверка существования шедулера на роутере.
        
        Аналогична verify_script_exists, но для системных шедулеров.
        Использует команду /system/scheduler/print для получения списка задач.
        
        Шедулеры в RouterOS:
        - Позволяют запускать скрипты по расписанию
        - Могут выполняться однократно или периодически
        - Поддерживают различные политики безопасности
        
        Args:
            scheduler_name (str): Имя шедулера для проверки
            
        Returns:
            bool: True если шедулер существует, False если нет
            
        Note:
            Используется для проверки перед созданием новых шедулеров
            и для очистки временных шедулеров после выполнения задач.
        """
        # Отправляем команду вывода шедулеров с фильтром по имени
        # =.proplist=.id,name - запрашиваем только ID и имя (избегаем пагинации)
        self.write_sentence(['/system/scheduler/print', f'?name={scheduler_name}', '=.proplist=.id,name'])
        
        exists = False  # Флаг существования шедулера
        
        # Обрабатываем ответы аналогично проверке скриптов
        while True:
            reply = self.read_sentence()
            if not reply:
                break
                
            if reply[0] == '!re':  # Строка данных шедулера
                # Ищем имя шедулера в параметрах
                for word in reply:
                    if word.startswith('=name=') and word[6:] == scheduler_name:
                        exists = True
                        break
            elif reply[0] == '!done':  # Конец вывода
                break
                
        return exists

    def remove_script(self, script_name):
        """
        Удаление скрипта с проверкой существования.
        
        Безопасный алгоритм удаления:
        1. Получаем ID скрипта через /system/script/print с фильтром
        2. Если скрипт найден - удаляем его по ID через /system/script/remove
        3. Ждем завершения операции (пауза 1 сек)
        4. Проверяем что скрипт действительно удален
        5. Возвращаем результат операции
        
        Использование ID вместо имени:
        - ID уникален и не может измениться
        - Избегает проблем с именами, содержащими специальные символы
        - Более надежный способ адресации объектов в RouterOS
        
        Args:
            script_name (str): Имя скрипта для удаления
            
        Returns:
            bool: True если удаление успешно или скрипт не существовал,
                  False если произошла ошибка при удалении
                  
        Note:
            Метод безопасен - если скрипт не существует, возвращает True.
            Это позволяет использовать его для "гарантированной очистки".
        """
        # Шаг 1: Ищем скрипт и получаем его внутренний ID
        self.write_sentence(['/system/script/print', f'?name={script_name}', '=.proplist=.id,name'])
        script_id = None  # ID скрипта в системе RouterOS
        
        # Читаем ответ и извлекаем ID
        while True:
            reply = self.read_sentence()
            if not reply:
                break
                
            if reply[0] == '!re':  # Строка с данными скрипта
                # Ищем параметр .id в ответе
                for word in reply:
                    if word.startswith('=.id='):
                        script_id = word[5:]  # Убираем префикс "=.id="
                        break
            elif reply[0] == '!done':
                break
        
        # Шаг 2: Если скрипт найден - удаляем его
        if script_id:
            # Удаляем скрипт по внутреннему ID
            self.write_sentence(['/system/script/remove', f'=.id={script_id}'])
            
            # Ждем подтверждения удаления
            while True:
                reply = self.read_sentence()
                if not reply or reply[0] == '!done':
                    break
            
            # Шаг 3: Умная проверка удаления
            for attempt in range(10):  # Максимум 10 попыток = 10 секунд
                time.sleep(1)
                
                # Переподключаемся для свежих данных
                if not self.reconnect_for_fresh_data():
                    continue
                    
                # Проверяем что скрипт удален
                if not self.verify_script_exists(script_name):
                    if attempt > 0:  # Показываем время только если было ожидание
                        print(f"✅ Скрипт удален через {attempt + 1} секунд")
                    return True
            
            print(f"❌ Ошибка: скрипт {script_name} не был удален за 10 секунд")
            return False
            
        # Скрипт не существует - считаем что цель достигнута
        return True

    def remove_scheduler(self, scheduler_name):
        """
        Удаление шедулера с проверкой существования.
        
        Безопасный алгоритм удаления (аналогично remove_script):
        1. Получаем ID шедулера через /system/scheduler/print с фильтром
        2. Если шедулер найден - удаляем его по ID через /system/scheduler/remove
        3. Ждем завершения операции (пауза 1 сек)
        4. Проверяем что шедулер действительно удален
        5. Возвращаем результат операции
        
        Использование ID вместо имени:
        - ID уникален и не может измениться
        - Избегает проблем с именами, содержащими специальные символы
        - Более надежный способ адресации объектов в RouterOS
        
        Args:
            scheduler_name (str): Имя шедулера для удаления
            
        Returns:
            bool: True если удаление успешно или шедулер не существовал,
                  False если произошла ошибка при удалении
                  
        Note:
            Метод безопасен - если шедулер не существует, возвращает True.
            Это позволяет использовать его для "гарантированной очистки".
        """
        # Шаг 1: Ищем шедулер и получаем его внутренний ID
        self.write_sentence(['/system/scheduler/print', f'?name={scheduler_name}', '=.proplist=.id,name'])
        scheduler_id = None  # ID шедулера в системе RouterOS
        
        # Читаем ответ и извлекаем ID
        while True:
            reply = self.read_sentence()
            if not reply:
                break
                
            if reply[0] == '!re':  # Строка с данными шедулера
                # Ищем параметр .id в ответе
                for word in reply:
                    if word.startswith('=.id='):
                        scheduler_id = word[5:]  # Убираем префикс "=.id="
                        break
            elif reply[0] == '!done':
                break
        
        # Шаг 2: Если шедулер найден - удаляем его
        if scheduler_id:
            # Удаляем шедулер по внутреннему ID
            self.write_sentence(['/system/scheduler/remove', f'=.id={scheduler_id}'])
            
            # Ждем подтверждения удаления
            while True:
                reply = self.read_sentence()
                if not reply or reply[0] == '!done':
                    break
            
            # Шаг 3: Умная проверка удаления шедулера
            for attempt in range(10):  # Максимум 10 попыток = 10 секунд
                time.sleep(1)
                
                # Переподключаемся для свежих данных
                if not self.reconnect_for_fresh_data():
                    continue
                    
                # Проверяем что шедулер удален
                if not self.verify_scheduler_exists(scheduler_name):
                    if attempt > 0:  # Показываем время только если было ожидание
                        print(f"✅ Шедулер удален через {attempt + 1} секунд")
                    return True
            
            print(f"❌ Ошибка: шедулер {scheduler_name} не был удален за 10 секунд")
            return False
            
        # Шедулер не существует - считаем что цель достигнута
        return True

    def reconnect_for_fresh_data(self):
        """
        Переподключение для получения свежих данных после асинхронных операций.
        
        Используется когда планировщики RouterOS выполняют операции асинхронно
        и старое API соединение может не видеть изменения.
        
        Returns:
            bool: True если переподключение успешно, False при ошибке
        """
        try:
            if hasattr(self, 'sock') and self.sock:
                self.sock.close()
                
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(60)
            self.sock.connect((self.router_ip, self.port))
            
            return self.login()
        except Exception as e:
            print(f"❌ Ошибка переподключения: {e}")
            return False

    def get_mikrotik_time(self):
        """
        Получение текущего времени с роутера для создания шедулеров.
        
        Использует команду /system/clock/print для получения системного времени роутера.
        Добавляет 5 секунд к текущему времени для создания шедулера в ближайшем будущем.
        
        Зачем нужно время роутера:
        - Шедулеры работают по времени роутера, не клиента
        - Избегаем проблем с разными часовыми поясами
        - Учитываем возможную разницу во времени между системами
        
        Логика добавления времени:
        - +5 секунд: достаточно для завершения создания шедулера
        - Обработка переполнения секунд/минут/часов
        - Корректная обработка перехода через полночь
        
        Returns:
            str: Время в формате HH:MM:SS для использования в шедулере
            None: При ошибке получения времени
            
        Example:
            Если текущее время роутера 14:30:25, метод вернет "14:30:30"
        """
        # Получаем информацию о системных часах роутера
        self.write_sentence(['/system/clock/print'])
        clock_data = self.read_sentence()
        
        # Ищем параметр времени в ответе
        for line in clock_data:
            if line.startswith('=time='):
                time_str = line[6:]  # Убираем префикс "=time="
                try:
                    # Парсим время в формате HH:MM:SS
                    h, m, s = map(int, time_str.split(':'))
                    
                    # Добавляем 5 секунд для запуска шедулера в будущем
                    s += 5
                    
                    # Обрабатываем переполнение времени
                    if s >= 60:  # Переполнение секунд
                        s -= 60
                        m += 1
                        if m >= 60:  # Переполнение минут
                            m -= 60
                            h += 1
                            if h >= 24:  # Переполнение часов (переход через полночь)
                                h -= 24
                                
                    # Возвращаем отформатированное время
                    return f"{h:02d}:{m:02d}:{s:02d}"
                except ValueError:
                    # Ошибка парсинга времени - прерываем обработку
                    break
                    
        return None  # Время не получено или произошла ошибка
    
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
            time.sleep(1)  # Сокращенная пауза для стабилизации

    def upload_large_script(self, script_name, content):
        """
        ═══════════════════════════════════════════════════════════════════
                    ЗАГРУЗКА БОЛЬШИХ СКРИПТОВ (>15KB)
        ═══════════════════════════════════════════════════════════════════
        
        Сложный метод для обхода ограничений RouterOS API на размер команды.
        
        ПРОБЛЕМА:
        RouterOS API ограничивает размер одной команды примерно 16KB.
        Попытка загрузить больший скрипт приводит к ошибке передачи.
        
        РЕШЕНИЕ - АРХИТЕКТУРА РАЗДЕЛЕНИЯ:
        ┌─────────────────────────────────────────────────────────────────┐
        │ 1. РАЗДЕЛЕНИЕ    │ Файл → части по 15KB                       │
        │ 2. ЗАГРУЗКА      │ Части → временные скрипты (-TEMP1, -TEMP2) │
        │ 3. ОБЪЕДИНИТЕЛЬ  │ Создание combine-скрипта                   │
        │ 4. ПЛАНИРОВЩИК   │ Scheduler для отложенного выполнения       │
        │ 5. ОБЪЕДИНЕНИЕ   │ Combine создает финальный скрипт           │
        │ 6. ОЧИСТКА       │ Удаление временных файлов и планировщика   │
        └─────────────────────────────────────────────────────────────────┘
        
        ПОЧЕМУ НУЖЕН SCHEDULER:
        - API команды выполняются синхронно в контексте подключения
        - Combine-скрипт должен выполниться независимо от API сессии
        - Scheduler обеспечивает асинхронное выполнение в нужное время
        
        СХЕМА ИМЕНОВАНИЯ:
        • Основной файл: "MyScript"
        • Временные части: "MyScript-TEMP1", "MyScript-TEMP2", ...
        • Объединяющий скрипт: "MyScript-Combine"
        • Планировщик: "run-MyScript-combine"
        
        Args:
            script_name (str): Имя итогового скрипта
            content (str): Полное содержимое скрипта (>15KB)
            
        Returns:
            bool: True при успешном объединении, False при ошибке
            
        КРИТИЧЕСКИЕ МОМЕНТЫ:
        - Время ожидания должно быть достаточным для выполнения
        - Все временные объекты должны быть очищены при ошибках
        - Проверка каждого этапа обязательна для надежности
        """
        print(f"\n📦 Загрузка большого скрипта {script_name} ({len(content)} байт)")
        print(f"⚠️  Размер превышает лимит API - используем разделение на части")
        
        try:
            # ═══ ЭТАП 1: ПОДГОТОВКА СОЕДИНЕНИЯ ═══
            # Создаем отдельное подключение для всей операции
            # Это обеспечивает изоляцию от других операций
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(60)
            sock.connect((self.router_ip, self.port))
            self.sock = sock
            
            if not self.login():
                return False
            
            # ═══ ЭТАП 2: РАЗДЕЛЕНИЕ НА ЧАСТИ ═══
            parts = []
            chunk_size = 15000  # Безопасный размер части (меньше лимита API)
            
            # Разделяем содержимое на равные части
            for start_pos in range(0, len(content), chunk_size):
                end_pos = start_pos + chunk_size
                part_content = content[start_pos:end_pos]
                parts.append(part_content)
            
            print(f"📑 Файл разделен на {len(parts)} частей по {chunk_size} байт")
            
            # ═══ ЭТАП 3: ЗАГРУЗКА ВРЕМЕННЫХ ЧАСТЕЙ ═══
            print(f"📤 Начинаем загрузку {len(parts)} временных частей...")
            
            for part_index, part_content in enumerate(parts, 1):
                temp_script_name = f"{script_name}-TEMP{part_index}"
                print(f"\n  📋 Часть {part_index}/{len(parts)}: {temp_script_name}")
                print(f"     Размер: {len(part_content)} байт")
                
                # Очистка старых временных скриптов (безопасность)
                if not self.remove_script(temp_script_name):
                    raise Exception(f"Не удалось очистить старый {temp_script_name}")
                
                # Загрузка части как отдельного скрипта
                self.write_sentence([
                    '/system/script/add',
                    f'=name={temp_script_name}',
                    f'=source={part_content}',
                    '=policy=read,write,policy,test'
                ])
                
                # Ожидание подтверждения загрузки
                upload_success = False
                while True:
                    reply = self.read_sentence()
                    if not reply:
                        break
                    if reply[0] == '!done':
                        upload_success = True
                        break
                    elif reply[0] == '!trap':
                        raise Exception(f"Ошибка загрузки части {part_index}: {reply}")
                
                if not upload_success:
                    raise Exception(f"Не получено подтверждение для части {part_index}")
                
                # Проверка успешности создания части
                if not self.verify_script_exists(temp_script_name):
                    raise Exception(f"Часть {temp_script_name} не найдена после загрузки")
                
                print(f"     ✅ {temp_script_name} успешно загружен")
                time.sleep(0.5)  # Краткая пауза между частями для стабильности
                
            # ═══ ЭТАП 4: СОЗДАНИЕ ОБЪЕДИНЯЮЩЕГО СКРИПТА ═══
            print(f"\n🔄 Создание объединяющего скрипта...")
            
            # Формируем код combine-скрипта на языке RouterOS
            combine_script_code = f"""# ════════════════════════════════════════════════════════════════
# АВТОМАТИЧЕСКИ СОЗДАННЫЙ ОБЪЕДИНЯЮЩИЙ СКРИПТ
# Скрипт: {script_name}
# Частей: {len(parts)}
# Создан: {time.strftime('%Y-%m-%d %H:%M:%S')}
# Система: MikrotikUploader v2.0
# ════════════════════════════════════════════════════════════════

:local finalContent ""
:local partContent ""

# === ЧТЕНИЕ И ОБЪЕДИНЕНИЕ ВСЕХ ЧАСТЕЙ ===
:log info "Начинаем объединение {len(parts)} частей скрипта {script_name}"
"""
            
            # Добавляем код для чтения каждой части
            for part_num in range(1, len(parts) + 1):
                combine_script_code += f"""
# --- Чтение части {part_num} ---
:log info "Читаем часть {part_num}: {script_name}-TEMP{part_num}"
:set partContent [/system script get {script_name}-TEMP{part_num} source]
:set finalContent ($finalContent . $partContent)
:log info "Часть {part_num} добавлена к общему содержимому"
"""
            
            # Добавляем создание финального скрипта
            combine_script_code += f"""
# === СОЗДАНИЕ ФИНАЛЬНОГО СКРИПТА ===
:log info "Создаем финальный скрипт: {script_name}"
/system script add name="{script_name}" source=$finalContent policy=read,write,policy,test
:log info "Финальный скрипт {script_name} создан успешно"

# === ОЧИСТКА ВРЕМЕННЫХ ФАЙЛОВ ===
:log info "Начинаем очистку временных файлов"
"""
            
            # Добавляем команды удаления всех временных частей
            for part_num in range(1, len(parts) + 1):
                combine_script_code += f"""
:log info "Удаляем временную часть: {script_name}-TEMP{part_num}"
/system script remove [find name="{script_name}-TEMP{part_num}"]
"""
            
            combine_script_code += f"""
:log info "Объединение скрипта {script_name} завершено успешно!"
"""
            
            # Вывод содержимого combine-скрипта для отладки
            print(f"\n📝 Содержимое объединяющего скрипта:")
            print("═" * 60)
            print(combine_script_code)
            print("═" * 60)
            
            # ═══ ЭТАП 5: ЗАГРУЗКА COMBINE-СКРИПТА ═══
            combine_script_name = f"{script_name}-Combine"
            print(f"\n📤 Загрузка объединяющего скрипта: {combine_script_name}")
            
            # Очистка старого combine-скрипта
            if not self.remove_script(combine_script_name):
                raise Exception(f"Не удалось очистить старый {combine_script_name}")
            
            # Загрузка combine-скрипта
            self.write_sentence([
                '/system/script/add',
                f'=name={combine_script_name}',
                f'=source={combine_script_code}',
                '=policy=read,write,policy,test'
            ])
            
            # Ожидание подтверждения
            combine_uploaded = False
            while True:
                reply = self.read_sentence()
                if not reply:
                    break
                if reply[0] == '!done':
                    combine_uploaded = True
                    break
                elif reply[0] == '!trap':
                    raise Exception(f"Ошибка загрузки combine-скрипта: {reply}")
            
            if not combine_uploaded:
                raise Exception("Не получено подтверждение загрузки combine-скрипта")
            
            # Проверка создания combine-скрипта
            if not self.verify_script_exists(combine_script_name):
                raise Exception(f"Combine-скрипт {combine_script_name} не найден после загрузки")
            
            print(f"✅ {combine_script_name} успешно загружен")
            
            # ═══ ЭТАП 6: СОЗДАНИЕ ПЛАНИРОВЩИКА ═══
            # Получаем системное время роутера для точного планирования
            execution_time = self.get_mikrotik_time()
            if not execution_time:
                raise Exception("Не удалось получить системное время роутера")
            
            scheduler_name = f"run-{script_name}-combine"
            print(f"⏰ Создание планировщика {scheduler_name} на время {execution_time}")
            
            # Очистка старого планировщика
            if not self.remove_scheduler(scheduler_name):
                raise Exception(f"Не удалось очистить старый планировщик {scheduler_name}")
            
            # Команда планировщика (многоэтапная):
            # 1. Запуск combine-скрипта
            # 2. Пауза 2 секунды для завершения
            # 3. Удаление combine-скрипта (самоочистка)
            # 4. Удаление самого планировщика (самоуничтожение)
            scheduler_command = (
                f"/system script run {script_name}-Combine; "
                f":delay 2s; "
                f"/system script remove {script_name}-Combine; "
                f"/system scheduler remove {scheduler_name}"
            )
            
            print(f"📋 Команда планировщика: {scheduler_command}")
            
            # Создание планировщика
            self.write_sentence([
                '/system/scheduler/add',
                f'=name={scheduler_name}',
                f'=on-event={scheduler_command}',
                f'=start-time={execution_time}',
                '=interval=0s',  # Однократное выполнение
                '=policy=read,write,policy,test'
            ])
            
            # Ожидание подтверждения создания планировщика
            scheduler_created = False
            while True:
                reply = self.read_sentence()
                if not reply:
                    break
                if reply[0] == '!done':
                    scheduler_created = True
                    break
                elif reply[0] == '!trap':
                    raise Exception(f"Ошибка создания планировщика: {reply}")
            
            if not scheduler_created:
                raise Exception("Не получено подтверждение создания планировщика")
            
            # ═══ ЭТАП 7: УМНОЕ ОЖИДАНИЕ ВЫПОЛНЕНИЯ ═══
            print(f"⏳ Ожидание автоматического объединения...")
            print(f"   Планировщик запустится в {execution_time}")
            print(f"   Максимальное время ожидания: 60 секунд")
            
            # Активная проверка создания финального скрипта
            script_created = False
            for attempt in range(60):  # Максимум 60 попыток = 60 секунд
                time.sleep(1)  # Пауза 1 секунда между проверками
                
                # Переподключаемся для получения свежих данных
                if not self.reconnect_for_fresh_data():
                    print(f"❌ Ошибка переподключения на попытке {attempt + 1}")
                    continue
                
                # Проверяем создание финального скрипта
                if self.verify_script_exists(script_name):
                    print(f"✅ Финальный скрипт создан через {attempt + 1} секунд!")
                    script_created = True
                    break
                
                # Показываем прогресс каждые 5 секунд
                if (attempt + 1) % 5 == 0:
                    print(f"   ⏳ Ожидание... ({attempt + 1}/60 сек)")
            
            if not script_created:
                raise Exception(f"Таймаут ожидания создания скрипта {script_name} (60 секунд)")
            
            # ═══ ЭТАП 8: ДИАГНОСТИКА ОЧИСТКИ ═══
            print(f"🔍 Диагностика очистки временных объектов:")
            
            # Проверяем что временные объекты удалены планировщиком
            for part_num in range(1, len(parts) + 1):
                temp_name = f"{script_name}-TEMP{part_num}"
                if self.verify_script_exists(temp_name):
                    print(f"   ⚠️  Временный скрипт {temp_name} ещё существует")
                else:
                    print(f"   ✅ Временный скрипт {temp_name} удален")
            
            combine_name = f"{script_name}-Combine"
            if self.verify_script_exists(combine_name):
                print(f"   ⚠️  Combine-скрипт {combine_name} ещё существует")
            else:
                print(f"   ✅ Combine-скрипт {combine_name} удален")
                
            scheduler_name = f"run-{script_name}-combine"
            if self.verify_scheduler_exists(scheduler_name):
                print(f"   ⚠️  Планировщик {scheduler_name} ещё существует")
            else:
                print(f"   ✅ Планировщик {scheduler_name} удален")
            
            print(f"✅ Большой скрипт {script_name} успешно загружен и объединен!")
            print(f"📊 Статистика: {len(parts)} частей → 1 финальный скрипт")
            
            self.uploaded_count += 1
            return True
            
        except Exception as error:
            print(f"❌ Критическая ошибка при загрузке большого файла:")
            print(f"   {error}")
            print(f"🧹 Рекомендуется ручная очистка временных объектов")
            self.failed_count += 1
            return False
        finally:
            # ═══ ОЧИСТКА РЕСУРСОВ ═══
            if 'sock' in locals():
                sock.close()
            # Сокращенная пауза для стабилизации системы после сложной операции
            time.sleep(1)

class RouterConfig:
    """Конфигурация роутера для подключения."""
    def __init__(self, name="", ip="", username="", password="", port=8728):
        self.name = name
        self.ip = ip
        self.username = username
        self.password = password
        self.port = port
    
    def to_dict(self):
        return {
            'name': self.name,
            'ip': self.ip,
            'username': self.username,
            'password': self.password,
            'port': self.port
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            data.get('name', ''),
            data.get('ip', ''),
            data.get('username', ''),
            data.get('password', ''),
            data.get('port', 8728)
        )

class MikrotikUploaderGUI:
    """Главный класс GUI приложения."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("MikrotikUploader GUI v2.1.2")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # Данные приложения
        self.routers = []  # Список роутеров
        self.selected_router = None  # Выбранный роутер
        self.source_directory = ""  # Папка с исходниками
        self.file_vars = {}  # Переменные для чекбоксов файлов
        self.log_queue = queue.Queue()  # Очередь для логов из потоков
        
        # Переменные для восстановления настроек
        self.saved_router_index = -1
        self.saved_column_widths = {}
        self.saved_window_geometry = ""
        
        # Настройки лога
        self.max_log_lines = 1000  # Максимальное количество строк в логе
        self.log_mode = "full"  # "full" или "compact"
        
        # Настройки автообновления
        self.auto_refresh_enabled = False
        self.auto_refresh_interval = 3  # Интервал в секундах (по умолчанию 3 сек)
        self.auto_refresh_timer = None
        self.last_refresh_time = None
        
        # Загружаем сохраненные настройки
        self.load_settings()
        
        # Создаем интерфейс
        self.create_interface()
        
        # Запускаем обработчик логов
        self.process_log_queue()
        
        # Обработчик закрытия приложения
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Показать окно поверх всех окон на 3 секунды
        self.show_window_on_top()
    
    def create_interface(self):
        """Создание основного интерфейса приложения."""
        # Создаем общий фрейм статуса внизу СНАЧАЛА (нужен для active_router_label)
        self.create_status_frame()
        
        # Создаем notebook для вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        
        # Создаем вкладки
        self.create_routers_tab()
        self.create_files_tab()
        self.create_content_tab()
        self.create_upload_tab()
    
    def create_routers_tab(self):
        """Вкладка управления роутерами."""
        routers_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(routers_frame, text="🌐 Роутеры")
        
        # Список роутеров
        list_frame = ttk.LabelFrame(routers_frame, text="Список роутеров", padding="5")
        list_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Treeview для роутеров
        columns = ("name", "ip", "username", "port")
        self.routers_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        # Заголовки колонок
        self.routers_tree.heading("name", text="Название")
        self.routers_tree.heading("ip", text="IP адрес")
        self.routers_tree.heading("username", text="Пользователь")
        self.routers_tree.heading("port", text="Порт")
        
        # Ширина колонок
        self.routers_tree.column("name", width=200)
        self.routers_tree.column("ip", width=150)
        self.routers_tree.column("username", width=120)
        self.routers_tree.column("port", width=80)
        
        # Скроллбар для списка
        scrollbar_routers = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.routers_tree.yview)
        self.routers_tree.configure(yscrollcommand=scrollbar_routers.set)
        
        self.routers_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_routers.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Привязываем обработчики событий
        self.routers_tree.bind("<Double-1>", lambda e: self.select_router_from_list())
        
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Кнопки управления роутерами
        buttons_frame = ttk.Frame(routers_frame)
        buttons_frame.grid(row=1, column=0, pady=10)
        
        ttk.Button(buttons_frame, text="➕ Добавить", command=self.add_router).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="✏️ Редактировать", command=self.edit_router).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="🗑️ Удалить", command=self.delete_router).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="🔗 Тест связи", command=self.test_connection).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="✅ Выбрать", command=self.select_router_from_list).pack(side=tk.LEFT)
        
        # Статус активного роутера - УБИРАЕМ, перенесен в общий фрейм статуса
        
        # Настройка растягивания для вкладки роутеров
        routers_frame.columnconfigure(0, weight=1)
        routers_frame.rowconfigure(0, weight=1)
        
        # Обновляем список роутеров
        self.refresh_routers_list()
    
    def create_status_frame(self):
        """Создание общего фрейма статуса внизу формы (отображается на всех вкладках)."""
        status_main_frame = ttk.LabelFrame(self.root, text="Статус и автообновление", padding="5")
        status_main_frame.pack(fill=tk.X, padx=10, pady=(10, 5), side=tk.BOTTOM)
        
        # Левая часть - информация о роутере
        router_info_frame = ttk.Frame(status_main_frame)
        router_info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(router_info_frame, text="Активный роутер:", font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        self.active_router_label = ttk.Label(router_info_frame, text="Роутер не выбран", 
                                           font=('Arial', 12), foreground='red')
        self.active_router_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Центральная часть - настройки автообновления
        auto_refresh_frame = ttk.Frame(status_main_frame)
        auto_refresh_frame.pack(side=tk.LEFT, padx=(10, 10))
        
        # Чекбокс автообновления
        self.auto_refresh_var = tk.BooleanVar(value=self.auto_refresh_enabled)
        auto_refresh_checkbox = ttk.Checkbutton(auto_refresh_frame, text="Автообновление", 
                                               variable=self.auto_refresh_var, 
                                               command=self.toggle_auto_refresh)
        auto_refresh_checkbox.pack(side=tk.LEFT, padx=(0, 10))
        
        # Выбор интервала
        ttk.Label(auto_refresh_frame, text="Интервал:", font=('Arial', 11)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.interval_var = tk.StringVar(value=str(self.auto_refresh_interval))
        interval_combo = ttk.Combobox(auto_refresh_frame, textvariable=self.interval_var, 
                                     values=["1", "3", "10"], width=5, state="readonly")
        interval_combo.pack(side=tk.LEFT, padx=(0, 5))
        interval_combo.bind("<<ComboboxSelected>>", self.on_interval_change)
        
        ttk.Label(auto_refresh_frame, text="сек", font=('Arial', 11)).pack(side=tk.LEFT, padx=(0, 15))
        
        # Кнопка ручного обновления
        ttk.Button(auto_refresh_frame, text="🔄 Обновить сейчас", 
                  command=self.manual_refresh).pack(side=tk.LEFT, padx=(0, 10))
        
        # Правая часть - статус последнего обновления
        refresh_status_frame = ttk.Frame(status_main_frame)
        refresh_status_frame.pack(side=tk.RIGHT)
        
        ttk.Label(refresh_status_frame, text="Последнее обновление:", font=('Arial', 11)).pack(side=tk.LEFT, padx=(0, 5))
        self.last_refresh_label = ttk.Label(refresh_status_frame, text="никогда", 
                                           font=('Arial', 11, 'bold'), foreground='gray')
        self.last_refresh_label.pack(side=tk.LEFT)
    
    def toggle_auto_refresh(self):
        """Включение/выключение автообновления."""
        self.auto_refresh_enabled = self.auto_refresh_var.get()
        
        if self.auto_refresh_enabled:
            if self.selected_router:
                self.log_message(f"🔄 Автообновление включено (интервал: {self.auto_refresh_interval} сек)", "INFO")
                self.start_auto_refresh()
            else:
                self.log_message("⚠️ Выберите роутер для включения автообновления", "WARNING")
                self.auto_refresh_var.set(False)
                self.auto_refresh_enabled = False
        else:
            self.log_message("⏹️ Автообновление отключено", "INFO")
            self.stop_auto_refresh()
        
        self.save_settings()
    
    def on_interval_change(self, event=None):
        """Изменение интервала автообновления."""
        try:
            new_interval = int(self.interval_var.get())
            if new_interval != self.auto_refresh_interval:
                self.auto_refresh_interval = new_interval
                self.log_message(f"⏱️ Интервал автообновления изменен на {new_interval} сек", "INFO")
                
                # Перезапускаем таймер с новым интервалом если автообновление включено
                if self.auto_refresh_enabled:
                    self.stop_auto_refresh()
                    self.start_auto_refresh()
                
                self.save_settings()
        except ValueError:
            self.log_message("❌ Некорректный интервал автообновления", "ERROR")
    
    def start_auto_refresh(self):
        """Запуск таймера автообновления."""
        if not self.selected_router:
            return
            
        self.stop_auto_refresh()  # Останавливаем предыдущий таймер если есть
        
        def auto_refresh_worker():
            if self.auto_refresh_enabled and self.selected_router:
                # Запускаем обновление в отдельном потоке чтобы не блокировать UI
                threading.Thread(target=self.auto_load_router_content_silent, daemon=True).start()
                
                # Планируем следующее обновление
                if self.auto_refresh_enabled:  # Проверяем еще раз на случай если отключили во время выполнения
                    self.auto_refresh_timer = self.root.after(self.auto_refresh_interval * 1000, auto_refresh_worker)
        
        # Запускаем первое обновление сразу
        auto_refresh_worker()
    
    def stop_auto_refresh(self):
        """Остановка таймера автообновления."""
        if self.auto_refresh_timer:
            self.root.after_cancel(self.auto_refresh_timer)
            self.auto_refresh_timer = None
    
    def manual_refresh(self):
        """Ручное обновление данных с роутера."""
        if not self.selected_router:
            messagebox.showwarning("Предупреждение", "Сначала выберите роутер")
            return
        
        self.log_message("🔄 Ручное обновление данных роутера", "INFO")
        threading.Thread(target=self.auto_load_router_content, daemon=True).start()
    
    def auto_load_router_content_silent(self):
        """Автоматическая загрузка содержимого роутера без подробного логирования."""
        if not self.selected_router:
            return
        
        try:
            uploader = MikrotikUploader()
            uploader.router_ip = self.selected_router.ip
            uploader.username = self.selected_router.username
            uploader.password = self.selected_router.password
            uploader.port = self.selected_router.port
            
            # Подключаемся с коротким таймаутом для автообновления
            uploader.connect()
            uploader.sock.settimeout(2.0)  # Короткий таймаут для автообновления
            
            if not uploader.login():
                raise Exception("Ошибка авторизации")
            
            # Получаем скрипты БЕЗ source поля
            uploader.write_sentence(['/system/script/print', '=.proplist=.id,name,owner,run-count'])
            scripts = []
            
            while True:
                try:
                    reply = uploader.read_sentence()
                    if not reply or reply[0] == '!done':
                        break
                    elif reply[0] == '!re':
                        script_info = {'name': '', 'owner': '', 'run-count': '0'}
                        for item in reply[1:]:
                            if item.startswith('=name='):
                                script_info['name'] = item[6:]
                            elif item.startswith('=owner='):
                                script_info['owner'] = item[7:]
                            elif item.startswith('=run-count='):
                                script_info['run-count'] = item[12:]
                        
                        if script_info['name']:
                            scripts.append(script_info)
                    elif reply[0] == '!trap':
                        break
                except:
                    break
            
            # Получаем шедулеры
            uploader.write_sentence(['/system/scheduler/print'])
            schedulers = []
            
            while True:
                try:
                    reply = uploader.read_sentence()
                    if not reply or reply[0] == '!done':
                        break
                    elif reply[0] == '!re':
                        scheduler_info = {'name': '', 'disabled': 'true', 'next-run': ''}
                        for item in reply[1:]:
                            if item.startswith('=name='):
                                scheduler_info['name'] = item[6:]
                            elif item.startswith('=disabled='):
                                scheduler_info['disabled'] = item[10:]
                            elif item.startswith('=next-run='):
                                scheduler_info['next-run'] = item[11:]
                        
                        if scheduler_info['name']:
                            schedulers.append(scheduler_info)
                    elif reply[0] == '!trap':
                        break
                except:
                    break
            
            uploader.sock.close()
            
            # Обновляем время последнего обновления
            self.last_refresh_time = datetime.now()
            
            def update_ui():
                # Обновляем UI
                if hasattr(self, 'router_scripts_tree'):
                    self.router_scripts_tree.delete(*self.router_scripts_tree.get_children())
                    for script in scripts:
                        run_count = script.get('run-count', '0')
                        self.router_scripts_tree.insert('', 'end', values=(script['name'], run_count))
                
                if hasattr(self, 'router_schedulers_tree'):
                    self.router_schedulers_tree.delete(*self.router_schedulers_tree.get_children())
                    for scheduler in schedulers:
                        status = "✓" if scheduler.get('disabled') == 'false' else "✗"
                        next_run = scheduler.get('next-run', 'никогда')
                        self.router_schedulers_tree.insert('', 'end', values=(scheduler['name'], status, next_run))
                
                if hasattr(self, 'remote_scripts_tree'):
                    self.remote_scripts_tree.delete(*self.remote_scripts_tree.get_children())
                    for script in scripts:
                        run_count = script.get('run-count', '0')
                        self.remote_scripts_tree.insert('', 'end', values=(script['name'], run_count))
                    
                    self.remote_status_var.set(f"Скриптов: {len(scripts)}, Шедулеров: {len(schedulers)}")
                
                if hasattr(self, 'content_status_var'):
                    self.content_status_var.set(f"Скриптов: {len(scripts)}, Шедулеров: {len(schedulers)}")
                
                # Обновляем время последнего обновления
                if hasattr(self, 'last_refresh_label'):
                    time_str = self.last_refresh_time.strftime("%H:%M:%S")
                    self.last_refresh_label.config(text=time_str, foreground='green')
            
            self.root.after(0, update_ui)
            
        except Exception as e:
            # При ошибке автообновления просто обновляем статус без детального логирования
            def update_error_status():
                if hasattr(self, 'last_refresh_label'):
                    self.last_refresh_label.config(text="ошибка", foreground='red')
                if hasattr(self, 'remote_status_var'):
                    self.remote_status_var.set("Ошибка подключения")
                if hasattr(self, 'content_status_var'):
                    self.content_status_var.set("Ошибка подключения")
            
            self.root.after(0, update_error_status)
    
    def create_files_tab(self):
        """Вкладка выбора файлов для загрузки."""
        files_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(files_frame, text="📁 Файлы")
        
        # Выбор папки с исходниками
        dir_frame = ttk.LabelFrame(files_frame, text="Папка с исходниками", padding="5")
        dir_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.source_dir_var = tk.StringVar()
        dir_entry = ttk.Entry(dir_frame, textvariable=self.source_dir_var, width=60)
        dir_entry.grid(row=0, column=0, padx=(0, 5))
        
        ttk.Button(dir_frame, text="📂 Обзор", command=self.browse_source_directory).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(dir_frame, text="🔍 Автопоиск", command=self.auto_find_directory).grid(row=0, column=2)
        
        # Создаем PanedWindow для разделения на две части
        paned_window = ttk.PanedWindow(files_frame, orient=tk.HORIZONTAL)
        paned_window.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        
        # ЛЕВАЯ ЧАСТЬ: Локальные файлы
        local_frame = ttk.LabelFrame(paned_window, text="Локальные файлы для загрузки", padding="5")
        paned_window.add(local_frame, weight=1)
        
        # Кнопки управления выбором файлов
        file_buttons_frame = ttk.Frame(local_frame)
        file_buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(file_buttons_frame, text="✅ Выбрать все", command=self.select_all_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(file_buttons_frame, text="❌ Снять все", command=self.deselect_all_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(file_buttons_frame, text="🔄 Обновить", command=self.refresh_files_list).pack(side=tk.LEFT)
        
        # Создаем Treeview для локальных файлов со стандартным выделением
        file_columns = ("name", "size", "modified")
        self.files_tree = ttk.Treeview(local_frame, columns=file_columns, show="headings", height=20, selectmode="extended")
        
        # Настройка колонок для файлов
        self.files_tree.heading("name", text="Имя файла ↕", command=lambda: self.sort_treeview(self.files_tree, "name", False))
        self.files_tree.heading("size", text="Размер (байт) ↕", command=lambda: self.sort_treeview(self.files_tree, "size", True))
        self.files_tree.heading("modified", text="Изменен ↕", command=lambda: self.sort_treeview(self.files_tree, "modified", False))
        
        self.files_tree.column("name", width=250, anchor=tk.W)
        self.files_tree.column("size", width=120, anchor=tk.E)
        self.files_tree.column("modified", width=180, anchor=tk.W)
        
        # Применяем стиль
        self.files_tree.configure(style="Custom.Treeview")
        
        # Привязываем обработчик выделения для автообновления информации о загрузке
        self.files_tree.bind("<<TreeviewSelect>>", lambda e: self.update_upload_info())
        
        scrollbar_files = ttk.Scrollbar(local_frame, orient=tk.VERTICAL, command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=scrollbar_files.set)
        
        self.files_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_files.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        local_frame.columnconfigure(0, weight=1)
        local_frame.rowconfigure(1, weight=1)
        
        
        # ПРАВАЯ ЧАСТЬ: Файлы на роутере
        remote_frame = ttk.LabelFrame(paned_window, text="Файлы на роутере", padding="5")
        paned_window.add(remote_frame, weight=1)
        
        # Кнопка обновления содержимого роутера
        remote_buttons_frame = ttk.Frame(remote_frame)
        remote_buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(remote_buttons_frame, text="🔄 Обновить", command=self.auto_load_router_content).pack(side=tk.LEFT, padx=(0, 5))
        self.remote_status_var = tk.StringVar(value="Выберите роутер")
        ttk.Label(remote_buttons_frame, textvariable=self.remote_status_var).pack(side=tk.LEFT)
        
        # Создаем Treeview для файлов на роутере (только скрипты)
        remote_columns = ("name", "size")
        self.remote_scripts_tree = ttk.Treeview(remote_frame, columns=remote_columns, show="headings", height=20)
        
        # Настройка колонок для удаленных файлов
        self.remote_scripts_tree.heading("name", text="Имя скрипта ↕", command=lambda: self.sort_treeview(self.remote_scripts_tree, "name", False))
        self.remote_scripts_tree.heading("size", text="Размер (байт) ↕", command=lambda: self.sort_treeview(self.remote_scripts_tree, "size", True))
        
        self.remote_scripts_tree.column("name", width=250, anchor=tk.W)
        self.remote_scripts_tree.column("size", width=120, anchor=tk.E)
        
        # Применяем стиль
        self.remote_scripts_tree.configure(style="Custom.Treeview")
        
        scrollbar_remote = ttk.Scrollbar(remote_frame, orient=tk.VERTICAL, command=self.remote_scripts_tree.yview)
        self.remote_scripts_tree.configure(yscrollcommand=scrollbar_remote.set)
        
        self.remote_scripts_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_remote.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        remote_frame.columnconfigure(0, weight=1)
        remote_frame.rowconfigure(1, weight=1)
        
        # Настройка растягивания
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(1, weight=1)
        
        # Переменные для работы с файлами удалены - используется стандартное выделение
    

    
    def create_content_tab(self):
        """Вкладка просмотра содержимого роутера."""
        content_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(content_frame, text="📋 Содержимое")
        
        # Кнопка подключения и управления
        connect_frame = ttk.Frame(content_frame)
        connect_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(connect_frame, text="🔌 Подключиться и получить список", 
                  command=self.auto_load_router_content).pack(side=tk.LEFT, padx=(0, 10))
        
        self.content_status_var = tk.StringVar(value="Не подключен")
        ttk.Label(connect_frame, textvariable=self.content_status_var).pack(side=tk.LEFT)
        
        # Главный PanedWindow - горизонтальное разделение (скрипты | правая часть)
        main_paned = ttk.PanedWindow(content_frame, orient=tk.HORIZONTAL)
        main_paned.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ЛЕВАЯ ЧАСТЬ: Скрипты с кнопками управления
        scripts_main_frame = ttk.Frame(main_paned)
        main_paned.add(scripts_main_frame, weight=1)
        
        scripts_frame = ttk.LabelFrame(scripts_main_frame, text="Скрипты на роутере", padding="5")
        scripts_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Кнопки управления скриптами
        scripts_buttons_frame = ttk.Frame(scripts_frame)
        scripts_buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(scripts_buttons_frame, text="🔄 Обновить", 
                  command=self.refresh_router_scripts).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(scripts_buttons_frame, text="🗑️ Удалить выбранные", 
                  command=self.delete_selected_scripts).pack(side=tk.LEFT)
        
        # Список скриптов
        script_columns = ("name", "size")
        self.router_scripts_tree = ttk.Treeview(scripts_frame, columns=script_columns, 
                                               show="headings", height=20, selectmode="extended")
        
        self.router_scripts_tree.heading("name", text="Имя скрипта ↕", 
                                         command=lambda: self.sort_treeview(self.router_scripts_tree, "name", False))
        self.router_scripts_tree.heading("size", text="Запуски ↕",
                                         command=lambda: self.sort_treeview(self.router_scripts_tree, "size", True))
        
        self.router_scripts_tree.column("name", width=280, anchor=tk.W)
        self.router_scripts_tree.column("size", width=100, anchor=tk.E)
        
        style = ttk.Style()
        style.configure("Custom.Treeview", font=('Arial', 12), rowheight=22)
        style.configure("Custom.Treeview.Heading", font=('Arial', 11, 'bold'))
        self.router_scripts_tree.configure(style="Custom.Treeview")
        
        scrollbar_router_scripts = ttk.Scrollbar(scripts_frame, orient=tk.VERTICAL, 
                                                command=self.router_scripts_tree.yview)
        self.router_scripts_tree.configure(yscrollcommand=scrollbar_router_scripts.set)
        
        self.router_scripts_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_router_scripts.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        scripts_frame.columnconfigure(0, weight=1)
        scripts_frame.rowconfigure(1, weight=1)
        scripts_main_frame.columnconfigure(0, weight=1)
        scripts_main_frame.rowconfigure(0, weight=1)
        
        # ПРАВАЯ ЧАСТЬ: Вертикальный PanedWindow для шедулеров и задач
        right_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned, weight=1)
        
        # ШЕДУЛЕРЫ (верхняя правая часть)
        schedulers_main_frame = ttk.Frame(right_paned)
        right_paned.add(schedulers_main_frame, weight=1)
        
        schedulers_frame = ttk.LabelFrame(schedulers_main_frame, text="Шедулеры на роутере", padding="5")
        schedulers_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Кнопки управления шедулерами
        schedulers_buttons_frame = ttk.Frame(schedulers_frame)
        schedulers_buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(schedulers_buttons_frame, text="🔄 Обновить", 
                  command=self.refresh_router_schedulers).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(schedulers_buttons_frame, text="🗑️ Удалить", 
                  command=self.delete_selected_schedulers).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(schedulers_buttons_frame, text="▶️ Включить", 
                  command=self.enable_selected_schedulers).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(schedulers_buttons_frame, text="⏸️ Отключить", 
                  command=self.disable_selected_schedulers).pack(side=tk.LEFT)
        
        # Список шедулеров
        scheduler_columns = ("name", "status", "next_run")
        self.router_schedulers_tree = ttk.Treeview(schedulers_frame, columns=scheduler_columns, 
                                                  show="headings", height=10, selectmode="extended")
        
        self.router_schedulers_tree.heading("name", text="Имя ↕", 
                                           command=lambda: self.sort_treeview(self.router_schedulers_tree, "name", False))
        self.router_schedulers_tree.heading("status", text="Статус ↕", 
                                           command=lambda: self.sort_treeview(self.router_schedulers_tree, "status", False))
        self.router_schedulers_tree.heading("next_run", text="Следующий запуск ↕", 
                                           command=lambda: self.sort_treeview(self.router_schedulers_tree, "next_run", False))
        
        self.router_schedulers_tree.column("name", width=180, anchor=tk.W)
        self.router_schedulers_tree.column("status", width=60, anchor=tk.CENTER)
        self.router_schedulers_tree.column("next_run", width=120, anchor=tk.W)
        
        self.router_schedulers_tree.configure(style="Custom.Treeview")
        
        scrollbar_router_schedulers = ttk.Scrollbar(schedulers_frame, orient=tk.VERTICAL, 
                                                   command=self.router_schedulers_tree.yview)
        self.router_schedulers_tree.configure(yscrollcommand=scrollbar_router_schedulers.set)
        
        self.router_schedulers_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_router_schedulers.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        schedulers_frame.columnconfigure(0, weight=1)
        schedulers_frame.rowconfigure(1, weight=1)
        schedulers_main_frame.columnconfigure(0, weight=1)
        schedulers_main_frame.rowconfigure(0, weight=1)
        
        # ЗАДАЧИ (нижняя правая часть)
        jobs_main_frame = ttk.Frame(right_paned)
        right_paned.add(jobs_main_frame, weight=1)
        
        jobs_frame = ttk.LabelFrame(jobs_main_frame, text="Задачи на роутере", padding="5")
        jobs_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Кнопки управления задачами
        jobs_buttons_frame = ttk.Frame(jobs_frame)
        jobs_buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(jobs_buttons_frame, text="🔄 Обновить", 
                  command=self.refresh_router_jobs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(jobs_buttons_frame, text="⏹️ Остановить", 
                  command=self.stop_selected_jobs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(jobs_buttons_frame, text="🧹 Удалить завершенные", 
                  command=self.remove_finished_jobs).pack(side=tk.LEFT)
        
        # Список задач
        job_columns = ("id", "script", "status", "duration")
        self.router_jobs_tree = ttk.Treeview(jobs_frame, columns=job_columns, 
                                            show="headings", height=8, selectmode="extended")
        
        self.router_jobs_tree.heading("id", text="ID ↕", 
                                     command=lambda: self.sort_treeview(self.router_jobs_tree, "id", True))
        self.router_jobs_tree.heading("script", text="Скрипт ↕", 
                                     command=lambda: self.sort_treeview(self.router_jobs_tree, "script", False))
        self.router_jobs_tree.heading("status", text="Статус ↕", 
                                     command=lambda: self.sort_treeview(self.router_jobs_tree, "status", False))
        self.router_jobs_tree.heading("duration", text="Длительность ↕", 
                                     command=lambda: self.sort_treeview(self.router_jobs_tree, "duration", False))
        
        self.router_jobs_tree.column("id", width=50, anchor=tk.CENTER)
        self.router_jobs_tree.column("script", width=150, anchor=tk.W)
        self.router_jobs_tree.column("status", width=70, anchor=tk.CENTER)
        self.router_jobs_tree.column("duration", width=90, anchor=tk.CENTER)
        
        self.router_jobs_tree.configure(style="Custom.Treeview")
        
        scrollbar_router_jobs = ttk.Scrollbar(jobs_frame, orient=tk.VERTICAL, 
                                             command=self.router_jobs_tree.yview)
        self.router_jobs_tree.configure(yscrollcommand=scrollbar_router_jobs.set)
        
        self.router_jobs_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_router_jobs.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        jobs_frame.columnconfigure(0, weight=1)
        jobs_frame.rowconfigure(1, weight=1)
        jobs_main_frame.columnconfigure(0, weight=1)
        jobs_main_frame.rowconfigure(0, weight=1)
        
        # Настройка растягивания главного фрейма
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(1, weight=1)
    
    def create_upload_tab(self):
        """Вкладка загрузки файлов."""
        upload_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(upload_frame, text="🚀 Загрузка")
        
        # Информация о предстоящей загрузке
        info_frame = ttk.LabelFrame(upload_frame, text="Информация о загрузке", padding="5")
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.upload_info_text = tk.Text(info_frame, height=4, state=tk.DISABLED)
        self.upload_info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        info_frame.columnconfigure(0, weight=1)
        
        # Прогресс загрузки
        progress_frame = ttk.LabelFrame(upload_frame, text="Прогресс", padding="5")
        progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.progress_label = ttk.Label(progress_frame, text="Готов к загрузке")
        self.progress_label.grid(row=1, column=0)
        
        progress_frame.columnconfigure(0, weight=1)
        
        # Кнопки управления
        control_frame = ttk.Frame(upload_frame)
        control_frame.grid(row=2, column=0, pady=(0, 10))
        
        self.start_button = ttk.Button(control_frame, text="🚀 Начать загрузку", 
                                     command=self.start_upload, state=tk.DISABLED)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="⏹️ Остановить", 
                                    command=self.stop_upload, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)
        
        # Лог операций
        log_frame = ttk.LabelFrame(upload_frame, text="Лог операций", padding="5")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Увеличиваем размер лога с увеличенным шрифтом
        self.log_text = scrolledtext.ScrolledText(log_frame, height=25, state=tk.DISABLED, 
                                                 font=('Consolas', 12))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Настройки лога - отдельный фрейм внизу
        log_settings_frame = ttk.LabelFrame(upload_frame, text="Настройки лога", padding="5")
        log_settings_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Button(log_settings_frame, text="🗑️ Очистить лог", command=self.clear_log).pack(side=tk.LEFT, padx=(0, 15))
        
        # Режим лога с переключателями
        ttk.Label(log_settings_frame, text="Режим лога:").pack(side=tk.LEFT, padx=(0, 8))
        self.log_mode_var = tk.StringVar(value=self.log_mode)
        
        ttk.Radiobutton(log_settings_frame, text="Полный", variable=self.log_mode_var, 
                       value="full", command=self.on_log_mode_change).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(log_settings_frame, text="Сжатый", variable=self.log_mode_var, 
                       value="compact", command=self.on_log_mode_change).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(log_settings_frame, text=f"Макс. строк: {self.max_log_lines}").pack(side=tk.LEFT)
        
        # Настройка растягивания
        upload_frame.columnconfigure(0, weight=1)
        upload_frame.rowconfigure(3, weight=1)  # Лог растягивается
        
        # Переменные для контроля загрузки
        self.upload_thread = None
        self.upload_stop_flag = threading.Event()
        
        # Обновляем информацию о загрузке
        self.update_upload_info()
        
        # Попытка автопоиска папки после создания всех элементов
        self.auto_find_directory()
        
        # Восстанавливаем настройки после создания всех элементов
        self.restore_ui_settings()
    
    def log_message(self, message, level="INFO"):
        """Логирование сообщений с поддержкой режимов и ограничения количества строк."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Формируем сообщение в зависимости от режима
        if self.log_mode == "compact":
            # Сокращенный режим - только важные сообщения
            if level in ["ERROR", "WARNING"]:
                formatted_message = f"[{timestamp}] {level}: {message}\n"
            elif "✅" in message or "❌" in message or "Загружено" in message or "завершена" in message:
                formatted_message = f"[{timestamp}] {message}\n"
            else:
                return  # Пропускаем обычные сообщения в сокращенном режиме
        else:
            # Полный режим - все сообщения
            formatted_message = f"[{timestamp}] {level}: {message}\n"
        
        # Добавляем в очередь для обработки в основном потоке
        self.log_queue.put(formatted_message)
    
    def update_window_title(self):
        """Обновление заголовка окна с именем выбранного роутера."""
        base_title = "MikrotikUploader GUI v1.0"
        if self.selected_router:
            new_title = f"{base_title} - {self.selected_router.name} ({self.selected_router.ip})"
        else:
            new_title = base_title
        self.root.title(new_title)
    
    def show_window_on_top(self):
        """Показать окно поверх всех на 3 секунды при запуске."""
        # Устанавливаем окно поверх всех
        self.root.attributes('-topmost', True)
        self.root.lift()
        self.root.focus_force()
        
        # Через 3 секунды убираем флаг topmost
        def remove_topmost():
            self.root.attributes('-topmost', False)
        
        self.root.after(3000, remove_topmost)  # 3000 мс = 3 секунды
    
    def restore_ui_settings(self):
        """Восстановление настроек интерфейса после создания всех элементов."""
        # Восстанавливаем выбранный роутер
        if hasattr(self, 'saved_router_index') and self.saved_router_index >= 0:
            if self.saved_router_index < len(self.routers):
                self.selected_router = self.routers[self.saved_router_index]
                # Выделяем строку в списке
                self.routers_tree.selection_set(str(self.saved_router_index))
                self.routers_tree.focus(str(self.saved_router_index))
                self.update_window_title()
                self.update_router_status()
                self.log_message(f"Восстановлен выбор роутера: {self.selected_router.name}")
        
        # Восстанавливаем ширины колонок
        if hasattr(self, 'saved_column_widths'):
            # Ширины колонок скриптов
            if 'scripts' in self.saved_column_widths:
                scripts_widths = self.saved_column_widths['scripts']
                if hasattr(self, 'router_scripts_tree'):
                    if 'name' in scripts_widths:
                        self.router_scripts_tree.column('name', width=scripts_widths['name'])
                    if 'size' in scripts_widths:
                        self.router_scripts_tree.column('size', width=scripts_widths['size'])
            
            # Ширины колонок шедулеров
            if 'schedulers' in self.saved_column_widths:
                schedulers_widths = self.saved_column_widths['schedulers']
                if hasattr(self, 'router_schedulers_tree'):
                    if 'name' in schedulers_widths:
                        self.router_schedulers_tree.column('name', width=schedulers_widths['name'])
                    if 'status' in schedulers_widths:
                        self.router_schedulers_tree.column('status', width=schedulers_widths['status'])
                    if 'next_run' in schedulers_widths:
                        self.router_schedulers_tree.column('next_run', width=schedulers_widths['next_run'])
            
            # Ширины колонок файлов
            if 'files' in self.saved_column_widths:
                files_widths = self.saved_column_widths['files']
                if hasattr(self, 'files_tree'):
                    if 'name' in files_widths:
                        self.files_tree.column('name', width=files_widths['name'])
                    if 'size' in files_widths:
                        self.files_tree.column('size', width=files_widths['size'])
                    if 'modified' in files_widths:
                        self.files_tree.column('modified', width=files_widths['modified'])
        
        # Восстанавливаем размер и положение окна
        if hasattr(self, 'saved_window_geometry') and self.saved_window_geometry:
            try:
                self.root.geometry(self.saved_window_geometry)
            except:
                pass  # Игнорируем ошибки восстановления геометрии
    
    def sort_treeview(self, tree, col, is_numeric, reverse=False):
        """Сортировка Treeview по указанной колонке."""
        data = [(tree.set(child, col), child) for child in tree.get_children('')]
        
        if is_numeric:
            # Числовая сортировка (для размеров файлов)
            try:
                data.sort(key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0, reverse=reverse)
            except:
                data.sort(reverse=reverse)
        else:
            # Алфавитная сортировка
            data.sort(key=lambda x: str(x[0]).lower(), reverse=reverse)
        
        # Переставляем элементы в нужном порядке
        for index, (val, child) in enumerate(data):
            tree.move(child, '', index)
        
        # Инвертируем направление сортировки для следующего клика
        next_reverse = not reverse
        if is_numeric:
            tree.heading(col, command=lambda: self.sort_treeview(tree, col, True, next_reverse))
        else:
            tree.heading(col, command=lambda: self.sort_treeview(tree, col, False, next_reverse))
    
    def process_log_queue(self):
        """Обработка очереди логов с ограничением количества строк."""
        try:
            messages_added = 0
            while messages_added < 10:  # Обрабатываем не более 10 сообщений за раз
                message = self.log_queue.get_nowait()
                
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, message)
                self.log_text.see(tk.END)
                
                # Проверяем количество строк и удаляем старые если нужно
                line_count = int(self.log_text.index('end-1c').split('.')[0])
                if line_count > self.max_log_lines:
                    # Удаляем первые строки, оставляя последние max_log_lines
                    lines_to_delete = line_count - self.max_log_lines
                    self.log_text.delete(1.0, f"{lines_to_delete + 1}.0")
                
                self.log_text.config(state=tk.DISABLED)
                messages_added += 1
                
        except queue.Empty:
            pass
        
        # Планируем следующую проверку
        self.root.after(100, self.process_log_queue)
    
    def load_settings(self):
        """Загрузка сохраненных настроек."""
        # Файл настроек ВСЕГДА создается рядом с модулем (абсолютный путь)
        module_dir = os.path.dirname(os.path.abspath(__file__))
        settings_file = os.path.join(module_dir, "uploader_settings.json")
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                # Загружаем роутеры
                self.routers = [RouterConfig.from_dict(router_data) 
                              for router_data in settings.get('routers', [])]
                
                # Загружаем последнюю папку
                self.source_directory = settings.get('source_directory', '')
                
                # Сохраняем индекс выбранного роутера для восстановления после создания интерфейса
                self.saved_router_index = settings.get('selected_router_index', -1)
                
                # Сохраняем ширины колонок для восстановления
                self.saved_column_widths = settings.get('column_widths', {})
                
                # Сохраняем настройки лога
                self.max_log_lines = settings.get('max_log_lines', 1000)
                self.log_mode = settings.get('log_mode', 'full')
                
                # Сохраняем настройки автообновления
                self.auto_refresh_enabled = settings.get('auto_refresh_enabled', False)
                self.auto_refresh_interval = settings.get('auto_refresh_interval', 3)
                
                # Сохраняем геометрию окна
                self.saved_window_geometry = settings.get('window_geometry', '')
                
        except Exception as e:
            self.log_message(f"Ошибка загрузки настроек: {e}", "ERROR")
    
    def save_settings(self):
        """Сохранение настроек."""
        # Файл настроек ВСЕГДА создается рядом с модулем (абсолютный путь)
        module_dir = os.path.dirname(os.path.abspath(__file__))
        settings_file = os.path.join(module_dir, "uploader_settings.json")
        try:
            # Сохраняем индекс выбранного роутера
            selected_router_index = -1
            if self.selected_router:
                try:
                    selected_router_index = self.routers.index(self.selected_router)
                except ValueError:
                    pass
            
            # Сохраняем ширины колонок
            column_widths = {}
            if hasattr(self, 'router_scripts_tree'):
                column_widths['scripts'] = {
                    'name': self.router_scripts_tree.column('name', 'width'),
                    'size': self.router_scripts_tree.column('size', 'width')
                }
            if hasattr(self, 'router_schedulers_tree'):
                column_widths['schedulers'] = {
                    'name': self.router_schedulers_tree.column('name', 'width'),
                    'status': self.router_schedulers_tree.column('status', 'width'),
                    'next_run': self.router_schedulers_tree.column('next_run', 'width')
                }
            if hasattr(self, 'files_tree'):
                column_widths['files'] = {
                    'name': self.files_tree.column('name', 'width'),
                    'size': self.files_tree.column('size', 'width'),
                    'modified': self.files_tree.column('modified', 'width')
                }
            
            # Сохраняем размер и положение окна
            window_geometry = self.root.geometry()
            
            settings = {
                'routers': [router.to_dict() for router in self.routers],
                'source_directory': self.source_directory,
                'selected_router_index': selected_router_index,
                'column_widths': column_widths,
                'window_geometry': window_geometry,
                'max_log_lines': self.max_log_lines,
                'log_mode': self.log_mode,
                'auto_refresh_enabled': self.auto_refresh_enabled,
                'auto_refresh_interval': self.auto_refresh_interval
            }
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.log_message(f"Ошибка сохранения настроек: {e}", "ERROR")
    
    def refresh_routers_list(self):
        """Обновление списка роутеров в интерфейсе."""
        # Очищаем список
        for item in self.routers_tree.get_children():
            self.routers_tree.delete(item)
        
        # Добавляем роутеры
        for i, router in enumerate(self.routers):
            self.routers_tree.insert("", tk.END, iid=i, values=(
                router.name, router.ip, router.username, router.port
            ))
        
        # Обновляем статус активного роутера
        self.update_router_status()
    
    def add_router(self):
        """Добавление нового роутера."""
        self.edit_router_dialog()
    
    def edit_router(self):
        """Редактирование выбранного роутера."""
        selection = self.routers_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите роутер для редактирования")
            return
        
        router_index = int(selection[0])
        self.edit_router_dialog(self.routers[router_index], router_index)
    
    def edit_router_dialog(self, router=None, index=None):
        """Диалог редактирования роутера."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить роутер" if router is None else "Редактировать роутер")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрируем диалог
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # Поля ввода
        fields = [
            ("Название:", "name"),
            ("IP адрес:", "ip"),
            ("Пользователь:", "username"),
            ("Пароль:", "password"),
            ("Порт:", "port")
        ]
        
        vars = {}
        for i, (label_text, field_name) in enumerate(fields):
            ttk.Label(dialog, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
            
            if field_name == "password":
                entry = ttk.Entry(dialog, show="*", width=30)
            else:
                entry = ttk.Entry(dialog, width=30)
            
            entry.grid(row=i, column=1, padx=10, pady=5)
            vars[field_name] = entry
            
            # Заполняем текущими значениями при редактировании
            if router:
                entry.insert(0, str(getattr(router, field_name)))
        
        # Кнопки
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)
        
        def save_router():
            try:
                # Создаем новый объект роутера
                new_router = RouterConfig(
                    name=vars["name"].get().strip(),
                    ip=vars["ip"].get().strip(),
                    username=vars["username"].get().strip(),
                    password=vars["password"].get(),
                    port=int(vars["port"].get() or 8728)
                )
                
                # Проверяем обязательные поля
                if not all([new_router.name, new_router.ip, new_router.username]):
                    messagebox.showerror("Ошибка", "Заполните обязательные поля")
                    return
                
                # Добавляем или обновляем роутер
                if index is None:
                    self.routers.append(new_router)
                else:
                    self.routers[index] = new_router
                
                self.refresh_routers_list()
                self.save_settings()
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("Ошибка", "Некорректный порт")
        
        ttk.Button(buttons_frame, text="Сохранить", command=save_router).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def delete_router(self):
        """Удаление выбранного роутера."""
        selection = self.routers_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите роутер для удаления")
            return
        
        router_index = int(selection[0])
        router = self.routers[router_index]
        
        if messagebox.askyesno("Подтверждение", f"Удалить роутер '{router.name}'?"):
            # Проверяем нужно ли сбросить выбранный роутер
            if self.selected_router == router:
                self.selected_router = None
                self.update_window_title()
            
            del self.routers[router_index]
            self.refresh_routers_list()
            self.save_settings()
    
    def test_connection(self):
        """Тест соединения с выбранным роутером."""
        selection = self.routers_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите роутер для тестирования")
            return
        
        router_index = int(selection[0])
        router = self.routers[router_index]
        
        def test_thread():
            try:
                uploader = MikrotikUploader()
                uploader.router_ip = router.ip
                uploader.username = router.username
                uploader.password = router.password
                uploader.port = router.port
                
                uploader.connect()
                success = uploader.login()
                uploader.sock.close()
                
                if success:
                    self.root.after(0, lambda: messagebox.showinfo("Успех", f"Соединение с {router.name} установлено!"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось войти на {router.name}"))
                    
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка соединения: {e}"))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def select_router_from_list(self):
        """Выбор активного роутера из выделенной строки списка."""
        selection = self.routers_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите роутер в списке")
            return
        
        router_index = int(selection[0])
        if router_index < len(self.routers):
            self.selected_router = self.routers[router_index]
            self.log_message(f"Выбран роутер: {self.selected_router.name} ({self.selected_router.ip})")
            self.update_window_title()
            self.update_router_status()
            self.update_upload_info()
            
            # Автоматически обновляем содержимое роутера
            self.auto_load_router_content()
            
            # Запускаем автообновление если оно было включено
            if self.auto_refresh_enabled:
                self.start_auto_refresh()
            
            # Запускаем автообновление если оно было включено
            if self.auto_refresh_enabled:
                self.start_auto_refresh()
    
    def update_router_status(self):
        """Обновление статуса активного роутера."""
        if self.selected_router:
            status_text = f"✅ {self.selected_router.name} ({self.selected_router.ip})"
            self.active_router_label.config(text=status_text, foreground='green')
            
            # Обновляем статус для правой панели файлов
            if hasattr(self, 'remote_status_var'):
                self.remote_status_var.set(f"Роутер: {self.selected_router.name}")
        else:
            self.active_router_label.config(text="❌ Роутер не выбран", foreground='red')
            
            # Очищаем статус для правой панели файлов
            if hasattr(self, 'remote_status_var'):
                self.remote_status_var.set("Выберите роутер")
    
    def browse_source_directory(self):
        """Выбор папки с исходниками."""
        directory = filedialog.askdirectory(
            title="Выберите папку с исходниками",
            initialdir=self.source_directory or os.getcwd()
        )
        
        if directory:
            self.source_directory = directory
            self.source_dir_var.set(directory)
            self.refresh_files_list()
            self.save_settings()
    
    def auto_find_directory(self):
        """Автоматический поиск папки CodeNasos."""
        codenosos_dir = find_codenosos_dir()
        if codenosos_dir:
            self.source_directory = codenosos_dir
            self.source_dir_var.set(codenosos_dir)
            self.refresh_files_list()
            self.log_message(f"Автоматически найдена папка: {codenosos_dir}")
        else:
            self.log_message("Папка CodeNasos не найдена автоматически", "WARNING")
    
    def refresh_files_list(self):
        """Обновление списка файлов."""
        # Очищаем дерево файлов
        self.files_tree.delete(*self.files_tree.get_children())
        
        if not self.source_directory or not os.path.exists(self.source_directory):
            return
        
        # Ищем .rsc файлы
        rsc_files = glob.glob(os.path.join(self.source_directory, '*.rsc'))
        
        if not rsc_files:
            return
        
        # Добавляем файлы в дерево
        for file_path in sorted(rsc_files):
            filename = os.path.basename(file_path)
            
            # Получаем размер файла
            try:
                file_size = os.path.getsize(file_path)
            except:
                file_size = 0
            
            # Получаем дату модификации
            try:
                mod_time = os.path.getmtime(file_path)
                mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M')
            except:
                mod_date = "неизвестно"
            
            # Добавляем элемент в дерево (стандартный список без чекбоксов)
            self.files_tree.insert('', 'end', values=(filename, file_size, mod_date))
        
        self.update_upload_info()
    
    def select_all_files(self):
        """Выбрать все файлы."""
        all_items = self.files_tree.get_children()
        self.files_tree.selection_set(all_items)
        self.update_upload_info()
    
    def deselect_all_files(self):
        """Снять выбор со всех файлов."""
        self.files_tree.selection_remove(self.files_tree.selection())
        self.update_upload_info()
    
    def update_upload_info(self):
        """Обновление информации о предстоящей загрузке."""
        # Проверяем что все элементы интерфейса созданы
        if not hasattr(self, 'upload_info_text') or not hasattr(self, 'start_button'):
            return
            
        # Получаем выбранные файлы через стандартное выделение
        selected_items = self.files_tree.selection()
        selected_files = []
        for item_id in selected_items:
            values = self.files_tree.item(item_id, 'values')
            if values:
                selected_files.append(values[0])  # Имя файла
        
        info_text = ""
        if self.selected_router:
            info_text += f"Роутер: {self.selected_router.name} ({self.selected_router.ip})\n"
        else:
            info_text += "Роутер: не выбран\n"
        
        info_text += f"Папка: {self.source_directory or 'не выбрана'}\n"
        info_text += f"Файлов к загрузке: {len(selected_files)}\n"
        
        if selected_files:
            info_text += f"Файлы: {', '.join(selected_files[:3])}"
            if len(selected_files) > 3:
                info_text += f" и еще {len(selected_files) - 3}"
        
        self.upload_info_text.config(state=tk.NORMAL)
        self.upload_info_text.delete(1.0, tk.END)
        self.upload_info_text.insert(1.0, info_text)
        self.upload_info_text.config(state=tk.DISABLED)
        
        # Активируем кнопку загрузки если все готово
        upload_in_progress = (self.upload_thread and self.upload_thread.is_alive())
        can_upload = (self.selected_router and 
                     self.source_directory and 
                     selected_files and 
                     not upload_in_progress)
        
        self.start_button.config(state=tk.NORMAL if can_upload else tk.DISABLED)
    

    
    def start_upload(self):
        """Запуск загрузки в отдельном потоке."""
        if self.upload_thread and self.upload_thread.is_alive():
            return
        
        # Очищаем старый поток если он завершился
        if self.upload_thread and not self.upload_thread.is_alive():
            self.upload_thread = None
        
        self.upload_stop_flag.clear()
        self.upload_thread = threading.Thread(target=self.upload_worker, daemon=True)
        self.upload_thread.start()
        
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
    
    def stop_upload(self):
        """Остановка загрузки."""
        self.upload_stop_flag.set()
        self.log_message("Запрошена остановка загрузки...", "WARNING")
    
    def upload_worker(self):
        """Рабочий поток загрузки файлов."""
        try:
            # Получаем выбранные файлы через стандартное выделение
            selected_items = self.files_tree.selection()
            selected_files = []
            for item_id in selected_items:
                values = self.files_tree.item(item_id, 'values')
                if values:
                    selected_files.append(values[0])  # Имя файла
            
            total_files = len(selected_files)
            
            self.log_message(f"🚀 Начинаем загрузку {total_files} файлов на {self.selected_router.name}")
            self.log_message(f"📁 Источник: {self.source_directory}")
            self.log_message(f"🎯 Роутер: {self.selected_router.ip}:{self.selected_router.port}")
            
            # Обновляем прогресс
            self.root.after(0, lambda: self.progress_bar.config(maximum=total_files, value=0))
            self.root.after(0, lambda: self.progress_label.config(text="Подготовка..."))
            
            uploaded_count = 0
            failed_count = 0
            
            for i, filename in enumerate(selected_files):
                if self.upload_stop_flag.is_set():
                    self.log_message("⏹️ Загрузка остановлена пользователем", "WARNING")
                    break
                
                file_path = os.path.join(self.source_directory, filename)
                script_name = filename.replace('.rsc', '')
                
                self.log_message(f"📄 [{i+1}/{total_files}] Обработка файла: {filename}")
                self.root.after(0, lambda filename=filename: self.progress_label.config(text=f"Загружаем {filename}..."))
                
                try:
                    # Читаем файл
                    self.log_message(f"📖 Чтение файла: {file_path}")
                    try:
                        with codecs.open(file_path, 'r', encoding='utf-8-sig') as f:
                            content = f.read()
                        self.log_message(f"✅ Файл прочитан в UTF-8, размер: {len(content)} символов")
                    except UnicodeDecodeError:
                        self.log_message("⚠️ Ошибка UTF-8, пробуем Windows-1251")
                        with codecs.open(file_path, 'r', encoding='windows-1251') as f:
                            content = f.read()
                        self.log_message(f"✅ Файл прочитан в Windows-1251, размер: {len(content)} символов")
                    
                    # Определяем тип загрузки
                    content_size = len(content.encode('utf-8'))
                    if content_size > 15000:
                        self.log_message(f"📦 Большой файл ({content_size} байт), будет разделен на части")
                    else:
                        self.log_message(f"📄 Обычный файл ({content_size} байт), прямая загрузка")
                    
                    # Создаем загрузчик
                    self.log_message(f"🔗 Создание подключения к роутеру")
                    uploader = MikrotikUploader()
                    uploader.router_ip = self.selected_router.ip
                    uploader.username = self.selected_router.username
                    uploader.password = self.selected_router.password
                    uploader.port = self.selected_router.port
                    
                    # Загружаем
                    self.log_message(f"⬆️ Начинаем загрузку скрипта: {script_name}")
                    if uploader.upload_script(script_name, content):
                        uploaded_count += 1
                        self.log_message(f"✅ {filename} загружен успешно")
                    else:
                        failed_count += 1
                        self.log_message(f"❌ Ошибка загрузки {filename}", "ERROR")
                
                except Exception as e:
                    failed_count += 1
                    self.log_message(f"❌ Ошибка обработки {filename}: {e}", "ERROR")
                
                # Обновляем прогресс
                self.root.after(0, lambda i=i: self.progress_bar.config(value=i+1))
                
                if self.upload_stop_flag.is_set():
                    break
            
            # Завершение
            if not self.upload_stop_flag.is_set():
                self.log_message(f"🎉 Загрузка завершена! Успешно: {uploaded_count}, Ошибок: {failed_count}")
                self.root.after(0, lambda: self.progress_label.config(text=f"Завершено: {uploaded_count}/{total_files}"))
            
        except Exception as e:
            self.log_message(f"❌ Критическая ошибка загрузки: {e}", "ERROR")
        finally:
            # Сбрасываем поток и возвращаем кнопки в исходное состояние
            self.upload_thread = None
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
            self.root.after(0, self.update_upload_info)
    
    def refresh_router_scripts(self):
        """Обновление списка скриптов на роутере"""
        if not self.selected_router:
            messagebox.showwarning("Предупреждение", "Сначала выберите роутер")
            return
        self.auto_load_router_content()
    
    def refresh_router_schedulers(self):
        """Обновление списка шедулеров на роутере"""
        if not self.selected_router:
            messagebox.showwarning("Предупреждение", "Сначала выберите роутер")
            return
        self.auto_load_router_content()
    
    def refresh_router_jobs(self):
        """Обновление списка задач на роутере"""
        if not self.selected_router:
            messagebox.showwarning("Предупреждение", "Сначала выберите роутер")
            return
        self.load_router_jobs()
    
    def delete_selected_scripts(self):
        """Удаление выбранных скриптов"""
        selected_items = self.router_scripts_tree.selection()
        if not selected_items:
            messagebox.showwarning("Предупреждение", "Выберите скрипты для удаления")
            return
        
        scripts_to_delete = []
        for item in selected_items:
            script_name = self.router_scripts_tree.item(item)['values'][0]
            scripts_to_delete.append(script_name)
        
        if messagebox.askyesno("Подтверждение", 
                              f"Удалить {len(scripts_to_delete)} скрипт(ов)?"):
            
            def delete_scripts_thread():
                try:
                    uploader = MikrotikUploader()
                    uploader.router_ip = self.selected_router.ip
                    uploader.username = self.selected_router.username
                    uploader.password = self.selected_router.password
                    uploader.port = self.selected_router.port
                    
                    uploader.connect()
                    if not uploader.login():
                        raise Exception("Ошибка авторизации")
                    
                    success_count = 0
                    for script_name in scripts_to_delete:
                        self.log_message(f"🗑️ Удаление скрипта: {script_name}", "INFO")
                        if uploader.remove_script(script_name):
                            success_count += 1
                            self.log_message(f"✅ Скрипт {script_name} удален", "INFO")
                        else:
                            self.log_message(f"❌ Ошибка удаления скрипта {script_name}", "ERROR")
                    
                    uploader.sock.close()
                    self.log_message(f"🎉 Удаление завершено: {success_count}/{len(scripts_to_delete)}", "INFO")
                    
                    # Обновляем списки
                    self.root.after(0, self.auto_load_router_content)
                    
                except Exception as e:
                    self.log_message(f"❌ Ошибка удаления скриптов: {e}", "ERROR")
                    
            threading.Thread(target=delete_scripts_thread, daemon=True).start()
    
    def delete_selected_schedulers(self):
        """Удаление выбранных шедулеров"""
        selected_items = self.router_schedulers_tree.selection()
        if not selected_items:
            messagebox.showwarning("Предупреждение", "Выберите шедулеры для удаления")
            return
        
        schedulers_to_delete = []
        for item in selected_items:
            scheduler_name = self.router_schedulers_tree.item(item)['values'][0]
            schedulers_to_delete.append(scheduler_name)
        
        if messagebox.askyesno("Подтверждение", 
                              f"Удалить {len(schedulers_to_delete)} шедулер(ов)?"):
            
            def delete_schedulers_thread():
                try:
                    uploader = MikrotikUploader()
                    uploader.router_ip = self.selected_router.ip
                    uploader.username = self.selected_router.username
                    uploader.password = self.selected_router.password
                    uploader.port = self.selected_router.port
                    
                    uploader.connect()
                    if not uploader.login():
                        raise Exception("Ошибка авторизации")
                    
                    success_count = 0
                    for scheduler_name in schedulers_to_delete:
                        self.log_message(f"🗑️ Удаление шедулера: {scheduler_name}", "INFO")
                        if uploader.remove_scheduler(scheduler_name):
                            success_count += 1
                            self.log_message(f"✅ Шедулер {scheduler_name} удален", "INFO")
                        else:
                            self.log_message(f"❌ Ошибка удаления шедулера {scheduler_name}", "ERROR")
                    
                    uploader.sock.close()
                    self.log_message(f"🎉 Удаление завершено: {success_count}/{len(schedulers_to_delete)}", "INFO")
                    
                    # Обновляем списки
                    self.root.after(0, self.auto_load_router_content)
                    
                except Exception as e:
                    self.log_message(f"❌ Ошибка удаления шедулеров: {e}", "ERROR")
                    
            threading.Thread(target=delete_schedulers_thread, daemon=True).start()
    
    def enable_selected_schedulers(self):
        """Включение выбранных шедулеров"""
        selected_items = self.router_schedulers_tree.selection()
        if not selected_items:
            messagebox.showwarning("Предупреждение", "Выберите шедулеры для включения")
            return
        
        schedulers_to_enable = []
        for item in selected_items:
            scheduler_name = self.router_schedulers_tree.item(item)['values'][0]
            schedulers_to_enable.append(scheduler_name)
        
        def enable_schedulers_thread():
            try:
                uploader = MikrotikUploader()
                uploader.router_ip = self.selected_router.ip
                uploader.username = self.selected_router.username
                uploader.password = self.selected_router.password
                uploader.port = self.selected_router.port
                
                uploader.connect()
                if not uploader.login():
                    raise Exception("Ошибка авторизации")
                
                success_count = 0
                for scheduler_name in schedulers_to_enable:
                    self.log_message(f"▶️ Включение шедулера: {scheduler_name}", "INFO")
                    
                    # Получаем ID шедулера
                    uploader.write_sentence(['/system/scheduler/print', f'?name={scheduler_name}'])
                    scheduler_id = None
                    
                    while True:
                        reply = uploader.read_sentence()
                        if not reply or reply[0] == '!done':
                            break
                        if reply[0] == '!re':
                            for item in reply:
                                if item.startswith('=.id='):
                                    scheduler_id = item[5:]
                                    break
                    
                    if scheduler_id:
                        # Включаем шедулер (disabled=false)
                        uploader.write_sentence(['/system/scheduler/set', f'=.id={scheduler_id}', '=disabled=false'])
                        reply = uploader.read_sentence()
                        if reply and reply[0] == '!done':
                            success_count += 1
                            self.log_message(f"✅ Шедулер {scheduler_name} включен", "INFO")
                        else:
                            self.log_message(f"❌ Ошибка включения шедулера {scheduler_name}", "ERROR")
                    else:
                        self.log_message(f"❌ Шедулер {scheduler_name} не найден", "ERROR")
                
                uploader.sock.close()
                self.log_message(f"🎉 Включение завершено: {success_count}/{len(schedulers_to_enable)}", "INFO")
                
                # Обновляем списки
                self.root.after(0, self.auto_load_router_content)
                
            except Exception as e:
                self.log_message(f"❌ Ошибка включения шедулеров: {e}", "ERROR")
                
        threading.Thread(target=enable_schedulers_thread, daemon=True).start()
    
    def disable_selected_schedulers(self):
        """Отключение выбранных шедулеров"""
        selected_items = self.router_schedulers_tree.selection()
        if not selected_items:
            messagebox.showwarning("Предупреждение", "Выберите шедулеры для отключения")
            return
        
        schedulers_to_disable = []
        for item in selected_items:
            scheduler_name = self.router_schedulers_tree.item(item)['values'][0]
            schedulers_to_disable.append(scheduler_name)
        
        def disable_schedulers_thread():
            try:
                uploader = MikrotikUploader()
                uploader.router_ip = self.selected_router.ip
                uploader.username = self.selected_router.username
                uploader.password = self.selected_router.password
                uploader.port = self.selected_router.port
                
                uploader.connect()
                if not uploader.login():
                    raise Exception("Ошибка авторизации")
                
                success_count = 0
                for scheduler_name in schedulers_to_disable:
                    self.log_message(f"⏸️ Отключение шедулера: {scheduler_name}", "INFO")
                    
                    # Получаем ID шедулера
                    uploader.write_sentence(['/system/scheduler/print', f'?name={scheduler_name}'])
                    scheduler_id = None
                    
                    while True:
                        reply = uploader.read_sentence()
                        if not reply or reply[0] == '!done':
                            break
                        if reply[0] == '!re':
                            for item in reply:
                                if item.startswith('=.id='):
                                    scheduler_id = item[5:]
                                    break
                    
                    if scheduler_id:
                        # Отключаем шедулер (disabled=true)
                        uploader.write_sentence(['/system/scheduler/set', f'=.id={scheduler_id}', '=disabled=true'])
                        reply = uploader.read_sentence()
                        if reply and reply[0] == '!done':
                            success_count += 1
                            self.log_message(f"✅ Шедулер {scheduler_name} отключен", "INFO")
                        else:
                            self.log_message(f"❌ Ошибка отключения шедулера {scheduler_name}", "ERROR")
                    else:
                        self.log_message(f"❌ Шедулер {scheduler_name} не найден", "ERROR")
                
                uploader.sock.close()
                self.log_message(f"🎉 Отключение завершено: {success_count}/{len(schedulers_to_disable)}", "INFO")
                
                # Обновляем списки
                self.root.after(0, self.auto_load_router_content)
                
            except Exception as e:
                self.log_message(f"❌ Ошибка отключения шедулеров: {e}", "ERROR")
                
        threading.Thread(target=disable_schedulers_thread, daemon=True).start()
    
    def stop_selected_jobs(self):
        """Остановка выбранных задач"""
        selected_items = self.router_jobs_tree.selection()
        if not selected_items:
            messagebox.showwarning("Предупреждение", "Выберите задачи для остановки")
            return
        
        jobs_to_stop = []
        for item in selected_items:
            job_id = self.router_jobs_tree.item(item)['values'][0]
            jobs_to_stop.append(job_id)
        
        def stop_jobs_thread():
            try:
                uploader = MikrotikUploader()
                uploader.router_ip = self.selected_router.ip
                uploader.username = self.selected_router.username
                uploader.password = self.selected_router.password
                uploader.port = self.selected_router.port
                
                uploader.connect()
                if not uploader.login():
                    raise Exception("Ошибка авторизации")
                
                success_count = 0
                for job_id in jobs_to_stop:
                    self.log_message(f"⏹️ Остановка задачи ID: {job_id}", "INFO")
                    
                    # Останавливаем задачу по ID
                    uploader.write_sentence(['/system/script/job/stop', f'=.id={job_id}'])
                    reply = uploader.read_sentence()
                    
                    if reply and reply[0] == '!done':
                        success_count += 1
                        self.log_message(f"✅ Задача {job_id} остановлена", "INFO")
                    else:
                        self.log_message(f"❌ Ошибка остановки задачи {job_id}: {reply}", "ERROR")
                
                uploader.sock.close()
                self.log_message(f"🎉 Остановка завершена: {success_count}/{len(jobs_to_stop)}", "INFO")
                
                # Обновляем списки задач
                self.root.after(0, self.load_router_jobs)
                
            except Exception as e:
                self.log_message(f"❌ Ошибка остановки задач: {e}", "ERROR")
                
        threading.Thread(target=stop_jobs_thread, daemon=True).start()
    
    def remove_finished_jobs(self):
        """Удаление завершенных задач"""
        def remove_jobs_thread():
            try:
                uploader = MikrotikUploader()
                uploader.router_ip = self.selected_router.ip
                uploader.username = self.selected_router.username
                uploader.password = self.selected_router.password
                uploader.port = self.selected_router.port
                
                uploader.connect()
                if not uploader.login():
                    raise Exception("Ошибка авторизации")
                
                # Получаем список всех задач
                uploader.write_sentence(['/system/script/job/print'])
                finished_jobs = []
                
                while True:
                    reply = uploader.read_sentence()
                    if not reply or reply[0] == '!done':
                        break
                    if reply[0] == '!re':
                        job_id = None
                        job_status = None
                        
                        for item in reply:
                            if item.startswith('=.id='):
                                job_id = item[5:]
                            elif item.startswith('=status='):
                                job_status = item[8:]
                        
                        # Собираем завершенные задачи (статус != running)
                        if job_id and job_status and job_status != 'running':
                            finished_jobs.append(job_id)
                
                # Удаляем завершенные задачи
                success_count = 0
                for job_id in finished_jobs:
                    self.log_message(f"🧹 Удаление завершенной задачи ID: {job_id}", "INFO")
                    
                    uploader.write_sentence(['/system/script/job/remove', f'=.id={job_id}'])
                    reply = uploader.read_sentence()
                    
                    if reply and reply[0] == '!done':
                        success_count += 1
                    else:
                        self.log_message(f"❌ Ошибка удаления задачи {job_id}: {reply}", "ERROR")
                
                uploader.sock.close()
                self.log_message(f"🎉 Удаление завершено: {success_count}/{len(finished_jobs)} завершенных задач", "INFO")
                
                # Обновляем списки задач
                self.root.after(0, self.load_router_jobs)
                
            except Exception as e:
                self.log_message(f"❌ Ошибка удаления завершенных задач: {e}", "ERROR")
                
        threading.Thread(target=remove_jobs_thread, daemon=True).start()
    
    def load_router_jobs(self):
        """Загрузка списка задач с роутера"""
        if not self.selected_router:
            return
        
        def load_jobs_thread():
            try:
                # Здесь будет код загрузки задач через API
                # Пока заглушка
                jobs = [
                    {"id": "1", "script": "test-script", "status": "running", "duration": "00:05:30"},
                    {"id": "2", "script": "backup-script", "status": "finished", "duration": "00:01:15"}
                ]
                
                def update_jobs_ui():
                    self.router_jobs_tree.delete(*self.router_jobs_tree.get_children())
                    for job in jobs:
                        self.router_jobs_tree.insert('', 'end', values=(
                            job['id'], job['script'], job['status'], job['duration']
                        ))
                
                self.root.after(0, update_jobs_ui)
                
            except Exception as e:
                self.log_message(f"Ошибка загрузки задач: {e}", "ERROR")
        
        threading.Thread(target=load_jobs_thread, daemon=True).start()

    def on_closing(self):
        """Обработчик закрытия приложения."""
        # Останавливаем автообновление
        self.stop_auto_refresh()
        
        # Останавливаем загрузку если она идет
        if self.upload_thread and self.upload_thread.is_alive():
            self.upload_stop_flag.set()
            self.upload_thread.join(timeout=2)
        
        # Сохраняем настройки
        self.save_settings()
        
        # Закрываем приложение
        self.root.destroy()

    def auto_load_router_content(self):
        """Автоматическая загрузка содержимого роутера без диалогов."""
        if not self.selected_router:
            return
        
        def auto_load_thread():
            try:
                self.log_message("🔗 Начинаем автообновление содержимого роутера", "INFO")
                
                uploader = MikrotikUploader()
                uploader.router_ip = self.selected_router.ip
                uploader.username = self.selected_router.username
                uploader.password = self.selected_router.password
                uploader.port = self.selected_router.port
                
                # Подключаемся и авторизуемся
                self.log_message(f"📡 Подключение к {self.selected_router.ip}:{self.selected_router.port}", "INFO")
                uploader.connect()
                
                # Устанавливаем разумный таймаут - 3 секунды
                uploader.sock.settimeout(3.0)
                self.log_message("⏱️ Установлен таймаут соединения: 3 сек", "INFO")
                
                self.log_message(f"🔐 Авторизация пользователя: {self.selected_router.username}", "INFO")
                if not uploader.login():
                    raise Exception("Ошибка авторизации")
                self.log_message("✅ Авторизация успешна", "INFO")
                
                # Получаем скрипты БЕЗ source поля (избегаем пагинацию)
                self.log_message("📜 Запрос списка скриптов БЕЗ source: /system/script/print .proplist", "INFO")
                uploader.write_sentence(['/system/script/print', '=.proplist=.id,name,owner,run-count'])
                scripts = []
                scripts_count = 0
                
                while True:
                    try:
                        reply = uploader.read_sentence()
                        if not reply:
                            self.log_message("⚠️ Получен пустой ответ", "INFO")
                            break
                            
                        if reply[0] == '!done':
                            # Получили завершающий маркер - все данные прочитаны
                            self.log_message("✅ Получен маркер завершения !done", "INFO")
                            break
                        elif reply[0] == '!re':
                            # Обрабатываем каждый скрипт БЕЗ source поля
                            script_info = {'name': '', 'owner': '', 'run-count': '0'}
                            for item in reply[1:]:  # Пропускаем !re
                                if item.startswith('=name='):
                                    script_info['name'] = item[6:]
                                elif item.startswith('=owner='):
                                    script_info['owner'] = item[7:]
                                elif item.startswith('=run-count='):
                                    script_info['run-count'] = item[12:]
                            
                            if script_info['name']:
                                scripts.append(script_info)
                                scripts_count += 1
                                run_count = script_info.get('run-count', '0')
                                self.log_message(f"📋 Скрипт {scripts_count}: {script_info['name']} (владелец: {script_info['owner']}, запусков: {run_count})", "INFO")
                        elif reply[0] == '!trap':
                            # Ошибка API - выходим
                            self.log_message(f"❌ API Error: {reply}", "ERROR")
                            break
                            
                    except Exception as e:
                        # Таймаут или другая ошибка - завершаем чтение
                        if scripts_count > 0:
                            # Если хоть что-то прочитали - это нормально
                            self.log_message(f"⏱️ Таймаут чтения, получено {scripts_count} скриптов", "INFO")
                            break
                        else:
                            raise e
                
                # Получаем шедулеры аналогично
                self.log_message("⏰ Запрос списка шедулеров: /system/scheduler/print", "INFO")
                uploader.write_sentence(['/system/scheduler/print'])
                schedulers = []
                schedulers_count = 0
                
                while True:
                    try:
                        reply = uploader.read_sentence()
                        if not reply:
                            self.log_message("⚠️ Получен пустой ответ шедулеров", "INFO")
                            break
                            
                        if reply[0] == '!done':
                            self.log_message("✅ Получен маркер завершения шедулеров !done", "INFO")
                            break
                        elif reply[0] == '!re':
                            scheduler_info = {'name': '', 'disabled': 'true', 'next-run': ''}
                            for item in reply[1:]:
                                if item.startswith('=name='):
                                    scheduler_info['name'] = item[6:]
                                elif item.startswith('=disabled='):
                                    scheduler_info['disabled'] = item[10:]
                                elif item.startswith('=next-run='):
                                    scheduler_info['next-run'] = item[11:]
                            
                            if scheduler_info['name']:
                                schedulers.append(scheduler_info)
                                schedulers_count += 1
                                status = "активен" if scheduler_info['disabled'] == 'false' else "отключен"
                                self.log_message(f"⏰ Шедулер {schedulers_count}: {scheduler_info['name']} ({status})", "INFO")
                        elif reply[0] == '!trap':
                            self.log_message(f"❌ Scheduler API Error: {reply}", "ERROR")
                            break
                            
                    except Exception as e:
                        if schedulers_count > 0:
                            self.log_message(f"⏱️ Таймаут чтения шедулеров, получено {schedulers_count}", "INFO")
                            break
                        else:
                            raise e
                
                # Закрываем соединение
                self.log_message("🔌 Закрытие соединения с роутером", "INFO")
                uploader.sock.close()
                
                self.log_message(f"🎯 Автообновление завершено: {len(scripts)} скриптов, {len(schedulers)} шедулеров", "INFO")
                
                def update_ui():
                    # Очищаем и обновляем скрипты в router_scripts_tree
                    self.router_scripts_tree.delete(*self.router_scripts_tree.get_children())
                    for script in scripts:
                        run_count = script.get('run-count', '0')
                        self.router_scripts_tree.insert('', 'end', values=(script['name'], run_count))
                    
                    # Очищаем и обновляем шедулеры в router_schedulers_tree
                    self.router_schedulers_tree.delete(*self.router_schedulers_tree.get_children())
                    for scheduler in schedulers:
                        status = "✓" if scheduler.get('disabled') == 'false' else "✗"
                        next_run = scheduler.get('next-run', 'никогда')
                        self.router_schedulers_tree.insert('', 'end', values=(scheduler['name'], status, next_run))
                    
                    # Обновляем список файлов на роутере
                    if hasattr(self, 'remote_scripts_tree'):
                        self.remote_scripts_tree.delete(*self.remote_scripts_tree.get_children())
                        for script in scripts:
                            run_count = script.get('run-count', '0')
                            self.remote_scripts_tree.insert('', 'end', values=(script['name'], run_count))
                        
                        # Обновляем статус с отладочной информацией
                        self.remote_status_var.set(f"Скриптов: {len(scripts)}, Шедулеров: {len(schedulers)}")
                        # Обновляем также статус вкладки "Содержимое"
                        self.content_status_var.set(f"Скриптов: {len(scripts)}, Шедулеров: {len(schedulers)}")
                
                # Обновляем UI в основном потоке
                self.root.after(0, update_ui)
                
            except Exception as e:
                self.log_message(f"Автообновление содержимого: {e}", "WARNING")
                
                def update_error_status():
                    if hasattr(self, 'remote_status_var'):
                        self.remote_status_var.set("Ошибка подключения")
                    if hasattr(self, 'content_status_var'):
                        self.content_status_var.set("Ошибка подключения")
                
                # Обновляем статус ошибки в UI потоке
                self.root.after(0, update_error_status)
        
        # Запускаем в отдельном потоке
        threading.Thread(target=auto_load_thread, daemon=True).start()

    def clear_log(self):
        """Очистка лога."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def on_log_mode_change(self):
        """Обработчик изменения режима лога."""
        self.log_mode = self.log_mode_var.get()
        mode_text = "Полный" if self.log_mode == "full" else "Сжатый"
        self.log_message(f"Изменен режим лога: {mode_text}", "INFO")

def main():
    """Главная функция запуска приложения."""
    root = tk.Tk()
    app = MikrotikUploaderGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()