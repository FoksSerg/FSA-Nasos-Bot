#!/usr/bin/env python3
"""
MikrotikUploader - Загрузчик скриптов на RouterOS через API протокол

Этот модуль реализует загрузку .rsc скриптов на роутеры Mikrotik через
бинарный API протокол. Поддерживает:
- Загрузку обычных скриптов (до 15KB)
- Загрузку больших скриптов с автоматическим разделением на части
- Проверку существования скриптов и шедулеров
- Автоматическое удаление старых версий
- Работу с различными кодировками (ASCII, UTF-8)

Протокол API Mikrotik:
- Использует TCP сокеты на порт 8728
- Каждое "слово" кодируется с длиной в начале
- "Предложение" - набор слов, заканчивающийся пустым словом
- Ответы начинаются с !done (успех), !trap (ошибка), !re (данные)

Автор: NasosRunner Project
Версия: 2.0 с поддержкой больших файлов
"""

import socket   # Для TCP подключения к API
import os       # Для работы с файловой системой
import codecs   # Для работы с различными кодировками файлов
import time     # Для пауз между операциями
import glob     # Для поиска файлов по маске
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
        self.write_sentence(['/system/script/print', f'?name={script_name}'])
        
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
        self.write_sentence(['/system/scheduler/print', f'?name={scheduler_name}'])
        
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
        self.write_sentence(['/system/script/print', f'?name={script_name}'])
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
            
            # Пауза для завершения операции на стороне RouterOS
            time.sleep(1)
            
            # Шаг 3: Проверяем что скрипт действительно удален
            if self.verify_script_exists(script_name):
                print(f"❌ Ошибка: скрипт {script_name} не был удален")
                return False
            return True
            
        # Скрипт не существует - считаем что цель достигнута
        return True

    def remove_scheduler(self, scheduler_name):
        """
        Удаление шедулера с проверкой.
        
        Использует команду /system/scheduler/remove с встроенной функцией find.
        Конструкция [find name=scheduler_name] автоматически находит ID шедулера
        по имени и передает его команде remove.
        
        Преимущества использования find:
        - Одна команда вместо двух (поиск + удаление)
        - Автоматическая обработка случая отсутствия объекта
        - Встроенная функция RouterOS, более эффективная
        
        Args:
            scheduler_name (str): Имя шедулера для удаления
            
        Returns:
            bool: True если удаление успешно, False при ошибке
            
        Note:
            Если шедулер не существует, команда завершается успешно без ошибок.
        """
        # Проверяем существование шедулера перед удалением
        if self.verify_scheduler_exists(scheduler_name):
            # Удаляем шедулер используя встроенную функцию find
            # [find name=...] возвращает ID объекта по имени
            self.write_sentence(['/system/scheduler/remove', f'=.id=[find name={scheduler_name}]'])
            reply = self.read_sentence()  # Читаем подтверждение
            
            # Пауза для завершения операции
            time.sleep(1)
            
            # Проверяем что шедулер действительно удален
            if self.verify_scheduler_exists(scheduler_name):
                print(f"❌ Ошибка: шедулер {scheduler_name} не был удален")
                return False
                
        return True

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
                time.sleep(2)  # Пауза между частями для стабильности
                
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
            
            # ═══ ЭТАП 7: ОЖИДАНИЕ ВЫПОЛНЕНИЯ ═══
            print(f"⏳ Ожидание автоматического объединения...")
            print(f"   Планировщик запустится в {execution_time}")
            print(f"   Процесс займет около 30 секунд...")
            
            # Увеличенное время ожидания для надежности
            # Учитываем время на выполнение combine-скрипта и очистку
            time.sleep(30)
            
            # ═══ ЭТАП 8: ПРОВЕРКА РЕЗУЛЬТАТА ═══
            print(f"🔍 Проверка результата объединения...")
            
            if not self.verify_script_exists(script_name):
                raise Exception(f"Финальный скрипт {script_name} не найден после объединения")
            
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
            # Пауза для стабилизации системы после сложной операции
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
        """Загрузка модулей с автоматическим поиском папки CodeNasos."""
        # Ищем папку CodeNasos начиная от текущего файла и поднимаясь вверх
        script_dir = find_codenosos_dir()
        
        if not script_dir:
            print("❌ Папка CodeNasos не найдена!")
            print("💡 Убедитесь что папка CodeNasos существует в проекте")
            return
        
        print(f"📁 Найдена папка CodeNasos: {script_dir}")
        
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
                    print(f"❌ Файл {name} не найден в {script_dir}")
        
        if not rsc_files:
            print("❌ Нет файлов для загрузки")
            print(f"📍 Поиск в: {script_dir}")
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
