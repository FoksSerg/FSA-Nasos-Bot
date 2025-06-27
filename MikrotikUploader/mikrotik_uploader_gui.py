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
from mikrotik_uploader import MikrotikUploader, find_codenosos_dir

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
        self.root.title("MikrotikUploader GUI v1.0")
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
        # Создаем notebook для вкладок (убираем верхний фрейм)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
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
        
        # Статус активного роутера
        status_frame = ttk.LabelFrame(routers_frame, text="Активный роутер", padding="5")
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.active_router_label = ttk.Label(status_frame, text="Роутер не выбран", 
                                           font=('Arial', 12, 'bold'), foreground='blue')
        self.active_router_label.pack()
        
        # Настройка растягивания для вкладки роутеров
        routers_frame.columnconfigure(0, weight=1)
        routers_frame.rowconfigure(0, weight=1)
        
        # Обновляем список роутеров
        self.refresh_routers_list()
    
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
        
        # Создаем Treeview для локальных файлов с чекбоксами
        file_columns = ("name", "size", "modified")
        self.files_tree = ttk.Treeview(local_frame, columns=file_columns, show="tree headings", height=20)
        
        # Настройка колонок для файлов
        self.files_tree.heading("#0", text="☑ Выбрать", command=lambda: self.sort_treeview(self.files_tree, "#0", False))
        self.files_tree.heading("name", text="Имя файла ↕", command=lambda: self.sort_treeview(self.files_tree, "name", False))
        self.files_tree.heading("size", text="Размер (байт) ↕", command=lambda: self.sort_treeview(self.files_tree, "size", True))
        self.files_tree.heading("modified", text="Изменен ↕", command=lambda: self.sort_treeview(self.files_tree, "modified", False))
        
        self.files_tree.column("#0", width=80, anchor=tk.CENTER)
        self.files_tree.column("name", width=200, anchor=tk.W)
        self.files_tree.column("size", width=100, anchor=tk.E)
        self.files_tree.column("modified", width=150, anchor=tk.W)
        
        # Применяем стиль
        self.files_tree.configure(style="Custom.Treeview")
        
        # Привязываем обработчик клика для чекбоксов
        self.files_tree.bind("<Button-1>", self.on_file_tree_click)
        
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
        
        # Переменные для работы с файлами
        self.file_vars = {}  # Словарь переменных чекбоксов для файлов
    
    def on_file_tree_click(self, event):
        """Обработчик клика по дереву файлов для переключения чекбоксов."""
        region = self.files_tree.identify_region(event.x, event.y)
        if region == "tree":
            item = self.files_tree.identify_row(event.y)
            if item:
                # Переключаем состояние чекбокса
                current_text = self.files_tree.item(item, "text")
                if current_text.startswith("☑"):
                    self.files_tree.item(item, text="☐")
                    self.file_vars[item] = False
                else:
                    self.files_tree.item(item, text="☑")
                    self.file_vars[item] = True
                
                # Обновляем информацию о загрузке
                self.update_upload_info()
                return "break"  # Предотвращаем стандартное поведение
    
    def create_content_tab(self):
        """Вкладка просмотра содержимого роутера."""
        content_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(content_frame, text="📋 Содержимое")
        
        # Кнопка подключения
        connect_frame = ttk.Frame(content_frame)
        connect_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(connect_frame, text="🔌 Подключиться и получить список", 
                  command=self.load_router_content).pack(side=tk.LEFT, padx=(0, 10))
        
        self.content_status_var = tk.StringVar(value="Не подключен")
        ttk.Label(connect_frame, textvariable=self.content_status_var).pack(side=tk.LEFT)
        
        # Списки содержимого
        lists_frame = ttk.Frame(content_frame)
        lists_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Скрипты
        scripts_frame = ttk.LabelFrame(lists_frame, text="Скрипты на роутере", padding="5")
        scripts_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Создаем Treeview для скриптов с колонками
        script_columns = ("name", "size")
        self.scripts_tree = ttk.Treeview(scripts_frame, columns=script_columns, show="headings", height=15)
        
        # Настройка колонок скриптов
        self.scripts_tree.heading("name", text="Имя скрипта ↕", command=lambda: self.sort_treeview(self.scripts_tree, "name", False))
        self.scripts_tree.heading("size", text="Размер (байт) ↕", command=lambda: self.sort_treeview(self.scripts_tree, "size", True))
        
        self.scripts_tree.column("name", width=300, anchor=tk.W)
        self.scripts_tree.column("size", width=150, anchor=tk.E)
        
        # Увеличиваем шрифт еще больше
        style = ttk.Style()
        style.configure("Custom.Treeview", font=('Arial', 14), rowheight=25)
        style.configure("Custom.Treeview.Heading", font=('Arial', 12, 'bold'))
        self.scripts_tree.configure(style="Custom.Treeview")
        
        scrollbar_scripts = ttk.Scrollbar(scripts_frame, orient=tk.VERTICAL, command=self.scripts_tree.yview)
        self.scripts_tree.configure(yscrollcommand=scrollbar_scripts.set)
        
        self.scripts_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_scripts.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        scripts_frame.columnconfigure(0, weight=1)
        scripts_frame.rowconfigure(0, weight=1)
        
        # Шедулеры
        schedulers_frame = ttk.LabelFrame(lists_frame, text="Шедулеры на роутере", padding="5")
        schedulers_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        # Создаем Treeview для шедулеров с колонками
        scheduler_columns = ("name", "status", "next_run")
        self.schedulers_tree = ttk.Treeview(schedulers_frame, columns=scheduler_columns, show="headings", height=15)
        
        # Настройка колонок шедулеров
        self.schedulers_tree.heading("name", text="Имя шедулера ↕", command=lambda: self.sort_treeview(self.schedulers_tree, "name", False))
        self.schedulers_tree.heading("status", text="Статус ↕", command=lambda: self.sort_treeview(self.schedulers_tree, "status", False))
        self.schedulers_tree.heading("next_run", text="Следующий запуск ↕", command=lambda: self.sort_treeview(self.schedulers_tree, "next_run", False))
        
        self.schedulers_tree.column("name", width=250, anchor=tk.W)
        self.schedulers_tree.column("status", width=100, anchor=tk.CENTER)
        self.schedulers_tree.column("next_run", width=200, anchor=tk.W)
        
        # Применяем тот же стиль шрифта
        self.schedulers_tree.configure(style="Custom.Treeview")
        
        scrollbar_schedulers = ttk.Scrollbar(schedulers_frame, orient=tk.VERTICAL, command=self.schedulers_tree.yview)
        self.schedulers_tree.configure(yscrollcommand=scrollbar_schedulers.set)
        
        self.schedulers_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_schedulers.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        schedulers_frame.columnconfigure(0, weight=1)
        schedulers_frame.rowconfigure(0, weight=1)
        
        # Настройка растягивания
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(1, weight=1)
        lists_frame.columnconfigure(0, weight=1)
        lists_frame.columnconfigure(1, weight=1)
        lists_frame.rowconfigure(0, weight=1)
    
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
                if 'name' in scripts_widths:
                    self.scripts_tree.column('name', width=scripts_widths['name'])
                if 'size' in scripts_widths:
                    self.scripts_tree.column('size', width=scripts_widths['size'])
            
            # Ширины колонок шедулеров
            if 'schedulers' in self.saved_column_widths:
                schedulers_widths = self.saved_column_widths['schedulers']
                if 'name' in schedulers_widths:
                    self.schedulers_tree.column('name', width=schedulers_widths['name'])
                if 'status' in schedulers_widths:
                    self.schedulers_tree.column('status', width=schedulers_widths['status'])
                if 'next_run' in schedulers_widths:
                    self.schedulers_tree.column('next_run', width=schedulers_widths['next_run'])
            
            # Ширины колонок файлов
            if 'files' in self.saved_column_widths:
                files_widths = self.saved_column_widths['files']
                if hasattr(self, 'files_tree'):
                    if 'selected' in files_widths:
                        self.files_tree.column('#0', width=files_widths['selected'])
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
            if hasattr(self, 'scripts_tree'):
                column_widths['scripts'] = {
                    'name': self.scripts_tree.column('name', 'width'),
                    'size': self.scripts_tree.column('size', 'width')
                }
            if hasattr(self, 'schedulers_tree'):
                column_widths['schedulers'] = {
                    'name': self.schedulers_tree.column('name', 'width'),
                    'status': self.schedulers_tree.column('status', 'width'),
                    'next_run': self.schedulers_tree.column('next_run', 'width')
                }
            if hasattr(self, 'files_tree'):
                column_widths['files'] = {
                    'selected': self.files_tree.column('#0', 'width'),
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
                'log_mode': self.log_mode
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
        self.file_vars.clear()
        
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
            
            # Добавляем элемент в дерево (по умолчанию не выбран)
            item_id = self.files_tree.insert('', 'end', 
                                           text="☐",  # Чекбокс не выбран
                                           values=(filename, file_size, mod_date))
            
            # Сохраняем состояние выбора
            self.file_vars[item_id] = False
        
        self.update_upload_info()
    
    def select_all_files(self):
        """Выбрать все файлы."""
        for item in self.files_tree.get_children():
            self.files_tree.item(item, text="☑")
            self.file_vars[item] = True
        self.update_upload_info()
    
    def deselect_all_files(self):
        """Снять выбор со всех файлов."""
        for item in self.files_tree.get_children():
            self.files_tree.item(item, text="☐")
            self.file_vars[item] = False
        self.update_upload_info()
    
    def update_upload_info(self):
        """Обновление информации о предстоящей загрузке."""
        # Проверяем что все элементы интерфейса созданы
        if not hasattr(self, 'upload_info_text') or not hasattr(self, 'start_button'):
            return
            
        selected_files = []
        for item_id, is_selected in self.file_vars.items():
            if is_selected:
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
    
    def load_router_content(self):
        """Загрузка содержимого роутера в отдельном потоке."""
        if not self.selected_router:
            messagebox.showwarning("Предупреждение", "Выберите роутер")
            return
        
        def load_content_thread():
            try:
                self.root.after(0, lambda: self.content_status_var.set("Подключение..."))
                
                uploader = MikrotikUploader()
                uploader.router_ip = self.selected_router.ip
                uploader.username = self.selected_router.username
                uploader.password = self.selected_router.password
                uploader.port = self.selected_router.port
                
                uploader.connect()
                # Устанавливаем разумный таймаут - 3 секунды  
                uploader.sock.settimeout(3.0)
                
                if not uploader.login():
                    raise Exception("Ошибка авторизации")
                
                # Получаем скрипты
                self.root.after(0, lambda: self.content_status_var.set("Получение скриптов..."))
                uploader.write_sentence(['/system/script/print'])
                
                scripts = []
                while True:
                    reply = uploader.read_sentence()
                    if not reply or reply[0] == '!done':
                        break
                    if reply[0] == '!re':
                        script_name = None
                        script_size = None
                        
                        # Собираем информацию о скрипте
                        for item in reply:
                            if item.startswith('=name='):
                                script_name = item[6:]
                            elif item.startswith('=source='):
                                # Если нет source-size, вычисляем размер из source
                                if script_size is None:
                                    script_size = len(item[8:])
                        
                        if script_name:
                            # Сохраняем как кортеж (имя, размер)
                            scripts.append((script_name, script_size or 0))
                
                # Получаем шедулеры
                self.root.after(0, lambda: self.content_status_var.set("Получение шедулеров..."))
                uploader.write_sentence(['/system/scheduler/print'])
                
                schedulers = []
                while True:
                    reply = uploader.read_sentence()
                    if not reply or reply[0] == '!done':
                        break
                    if reply[0] == '!re':
                        scheduler_name = None
                        scheduler_status = None
                        next_run = None
                        
                        # Собираем информацию о шедулере
                        for item in reply:
                            if item.startswith('=name='):
                                scheduler_name = item[6:]
                            elif item.startswith('=disabled='):
                                scheduler_status = "отключен" if item[10:] == "true" else "активен"
                            elif item.startswith('=next-run='):
                                next_run = item[11:]
                        
                        if scheduler_name:
                            # Сохраняем как кортеж (имя, статус, время)
                            schedulers.append((scheduler_name, scheduler_status or "неизвестно", next_run or "-"))
                
                uploader.sock.close()
                
                # Обновляем интерфейс
                def update_lists():
                    # Очищаем и заполняем скрипты
                    for item in self.scripts_tree.get_children():
                        self.scripts_tree.delete(item)
                    
                    for script_name, script_size in sorted(scripts):
                        self.scripts_tree.insert("", tk.END, values=(script_name, script_size))
                    
                    # Очищаем и заполняем шедулеры
                    for item in self.schedulers_tree.get_children():
                        self.schedulers_tree.delete(item)
                    
                    for scheduler_name, status, next_run in sorted(schedulers):
                        self.schedulers_tree.insert("", tk.END, values=(scheduler_name, status, next_run))
                    
                    self.content_status_var.set(f"Скриптов: {len(scripts)}, Шедулеров: {len(schedulers)}")
                
                self.root.after(0, update_lists)
                
            except Exception as e:
                self.root.after(0, lambda: self.content_status_var.set(f"Ошибка: {e}"))
        
        threading.Thread(target=load_content_thread, daemon=True).start()
    
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
            # Получаем выбранные файлы из нового интерфейса
            selected_files = []
            for item_id, is_selected in self.file_vars.items():
                if is_selected:
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
    
    def on_closing(self):
        """Обработчик закрытия приложения."""
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
                
                # Получаем скрипты с улучшенным чтением
                self.log_message("📜 Запрос списка скриптов: /system/script/print", "INFO")
                uploader.write_sentence(['/system/script/print'])
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
                            # Обрабатываем каждый скрипт
                            script_info = {'name': '', 'source': ''}
                            for item in reply[1:]:  # Пропускаем !re
                                if item.startswith('=name='):
                                    script_info['name'] = item[6:]
                                elif item.startswith('=source='):
                                    script_info['source'] = item[8:]
                            
                            if script_info['name']:
                                scripts.append(script_info)
                                scripts_count += 1
                                self.log_message(f"📋 Скрипт {scripts_count}: {script_info['name']} ({len(script_info.get('source', ''))} байт)", "INFO")
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
                    # Очищаем и обновляем скрипты
                    self.scripts_tree.delete(*self.scripts_tree.get_children())
                    for script in scripts:
                        size = f"{len(script.get('source', ''))}"
                        self.scripts_tree.insert('', 'end', values=(script['name'], size))
                    
                    # Очищаем и обновляем шедулеры
                    self.schedulers_tree.delete(*self.schedulers_tree.get_children())
                    for scheduler in schedulers:
                        status = "✓" if scheduler.get('disabled') == 'false' else "✗"
                        next_run = scheduler.get('next-run', 'никогда')
                        self.schedulers_tree.insert('', 'end', values=(scheduler['name'], status, next_run))
                    
                    # Обновляем список файлов на роутере
                    if hasattr(self, 'remote_scripts_tree'):
                        self.remote_scripts_tree.delete(*self.remote_scripts_tree.get_children())
                        for script in scripts:
                            size = f"{len(script.get('source', ''))}"
                            self.remote_scripts_tree.insert('', 'end', values=(script['name'], size))
                        
                        # Обновляем статус с отладочной информацией
                        self.remote_status_var.set(f"Скриптов: {len(scripts)}, Шедулеров: {len(schedulers)}")
                
                # Обновляем UI в основном потоке
                self.root.after(0, update_ui)
                
            except Exception as e:
                self.log_message(f"Автообновление содержимого: {e}", "WARNING")
                
                def update_error_status():
                    if hasattr(self, 'remote_status_var'):
                        self.remote_status_var.set("Ошибка подключения")
                
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