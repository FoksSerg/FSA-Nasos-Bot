import tkinter as tk
from tkinter import ttk
import urllib.parse
import pyperclip

class ToastNotification:
    def __init__(self, message, duration=2000):
        self.toast = tk.Toplevel()
        self.toast.overrideredirect(True)  # Убираем рамку окна
        
        # Делаем окно полупрозрачным
        self.toast.attributes('-alpha', 0.9)
        
        # Создаем фрейм с фоном
        frame = ttk.Frame(self.toast, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Добавляем текст
        label = ttk.Label(frame, text=message, font=('Arial', 12))
        label.pack()
        
        # Получаем размеры экрана
        screen_width = self.toast.winfo_screenwidth()
        screen_height = self.toast.winfo_screenheight()
        
        # Обновляем окно для получения его размеров
        self.toast.update_idletasks()
        width = self.toast.winfo_width()
        height = self.toast.winfo_height()
        
        # Вычисляем позицию для центрирования
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # Устанавливаем позицию
        self.toast.geometry(f'+{x}+{y}')
        
        # Устанавливаем окно поверх всех
        self.toast.attributes('-topmost', True)
        
        # Закрываем окно через указанное время
        self.toast.after(duration, self.toast.destroy)

class URLEncoder:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("RouterOS URL Encoder")
        self.window.geometry("1000x800")
        
        # Настройка шрифта
        self.default_font = ('Arial', 12)
        self.window.option_add('*Font', self.default_font)
        
        # Делаем окно невидимым на время создания
        self.window.withdraw()
        
        # Расширенный список эмодзи (разные тематики, без дубликатов)
        self.emojis = [
            # Цифры
            "0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🄼", "🄷", "🅂", "🅗", "🅜", "🅢", "🆗", "🆖", "🆘", 
            # Технические значки
            "⚙️", "🔧", "🔨", "🔩", "⚡", "🔌", "💻", "📱", "⌚", "⌨️", "🖥️", "🖨️", "🖱️", "🖲️", "🕹️", "🗜️", "💽", "💾", "💿", "📀",
            # Математические символы
            "➕", "➖", "✖️", "➗", "➰", "➿", "⚖️", "⚛️", "⚜️", "⚕️", "⚔️", "⚓", "📜", "🔄",
            # Основные
            "🚀", "✅", "🔥", "💪", "👍", "❌", "📊", "📈", "📉", "🔴", "🟢", "🟡", "⚪", "⚫", "💯", "❗", "❓", "📌", "🔔", "🎯",
            # Транспорт
            "🚗", "🚕", "🚙", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒", "🚐", "🚚", "🚛", "🚜", "🛵", "🏍️", "🚲", "🛴", "🚨", "🚁", "✈️",
            # Животные
            "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🦄", "🐔", "🐧", "🐦", "🐤",
            # Еда
            "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐", "🍈", "🍒", "🍑", "🥭", "🍍", "🥥", "🥝", "🍅", "🍆", "🥑",
            # Символы
            "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟", "☮️",
            # Техника
            "⌚", "💻", "⌨️", "🖥️", "🖨️", "🖱️", "🖲️", "🕹️", "🗜️", "💽", "💾", "💿", "📀", "📼", "📸", "🎥", "📽️", "📱", "📲", "📺",
            # Смайлики
            "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚",
            # Жесты
            "👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "🤏", "✌️", "🤞", "🤟", "🤘", "🤙", "👈", "👉", "👆", "🖕", "👇", "☝️", "👏",
            # Спорт
            "⚽", "🏀", "🏈", "⚾", "🎾", "🏐", "🏉", "🥏", "🎱", "🏓", "🏸", "🥅", "🏒", "🏑", "🏏", "🥍", "🏹", "🎣", "🥊", "🥋",
            # Погода
            "☀️", "🌤️", "⛅", "🌥️", "☁️", "🌦️", "🌧️", "⛈️", "🌩️", "🌨️", "❄️", "☃️", "⛄", "🌬️", "💨", "🌪️", "🌫️", "🌈", "☔", "💧",
            # Природа
            "🌱", "🌿", "🍀", "🌳", "🌲", "🌴", "🌵", "🌾", "🌺", "🌸", "🌼", "🌻", "🌞", "🌝", "🌛", "🌜", "🌚", "🌙", "🌎", "🌍",
            # Еда и напитки
            "🍕", "🍔", "🍟", "🍿", "🍩", "🍪", "🍫", "🍬", "🍭", "🍮", "🍯", "🍵", "☕", "🍺", "🍷", "🍸", "🍹", "🍾", "🥂", "🥃",
            # Предметы
            "📎", "📌", "🔍", "🔎", "🔐", "🔑", "🔒", "🔓", "🎁", "🎀", "🎈", "🎉", "🎊", "🎯", "🎲", "🎮", "🎰", "🎨", "🎭", "🎪",
            # Символы и знаки
            "⭐", "🌟", "✨", "💥", "💫", "💢", "💦", "💨", "💭", "💬", "💤", "⏰", "⏱️", "⏲️", "⌚", "⌛", "⏳", "🅾️", "��️", "🚰"
        ]
        
        # Создаем множество для быстрой проверки эмодзи
        self.valid_emojis = set(self.emojis)
        
        self.create_widgets()
        
        # Центрируем окно на экране
        self.center_window()
        
        # Показываем окно с эффектом
        self.show_window_with_effect()
        
    def center_window(self):
        # Получаем размеры экрана
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # Получаем размеры окна
        window_width = 1000
        window_height = 800
        
        # Вычисляем позицию для центрирования
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Устанавливаем позицию
        self.window.geometry(f'{window_width}x{window_height}+{x}+{y}')
        
    def show_window_with_effect(self):
        # Делаем окно поверх всех
        self.window.attributes('-topmost', True)
        
        # Показываем окно
        self.window.deiconify()
        
        # Через 2 секунды убираем флаг topmost
        self.window.after(2000, lambda: self.window.attributes('-topmost', False))
        
    def create_widgets(self):
        # Поле ввода текста
        input_frame = ttk.LabelFrame(self.window, text="Исходный текст", padding=10)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        input_btn_frame = ttk.Frame(input_frame)
        input_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(input_btn_frame, text="Вставить из буфера", 
                  command=lambda: self.paste_text(self.text_input)).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_btn_frame, text="Копировать в буфер", 
                  command=lambda: self.copy_from_text(self.text_input)).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_btn_frame, text="Очистить", 
                  command=lambda: self.clear_text(self.text_input)).pack(side=tk.LEFT, padx=5)
        
        self.text_input = tk.Text(input_frame, height=5, wrap=tk.WORD, font=self.default_font)
        self.text_input.pack(fill=tk.X)
        
        # --- Эмодзи с прокруткой ---
        emoji_frame = ttk.LabelFrame(self.window, text="Эмодзи", padding=10)
        emoji_frame.pack(fill=tk.X, padx=10, pady=5)

        emoji_canvas = tk.Canvas(emoji_frame, height=340)
        emoji_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        emoji_scrollbar = ttk.Scrollbar(emoji_frame, orient="vertical", command=emoji_canvas.yview)
        emoji_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        emoji_canvas.configure(yscrollcommand=emoji_scrollbar.set)

        emoji_inner = ttk.Frame(emoji_canvas)
        emoji_canvas.create_window((0, 0), window=emoji_inner, anchor='nw')

        # 20 эмодзи в строке
        for i, emoji in enumerate(self.emojis):
            row = i // 20
            col = i % 20
            btn = ttk.Button(emoji_inner, text=emoji, width=2,
                           command=lambda e=emoji: self.insert_emoji(e))
            btn.grid(row=row, column=col, padx=(1, 4), pady=1)  # справа чуть больше отступ

        emoji_inner.update_idletasks()
        emoji_canvas.config(scrollregion=emoji_canvas.bbox("all"))

        def _on_mousewheel(event):
            if emoji_canvas.winfo_height() < emoji_inner.winfo_height():
                delta = -3 if event.delta > 0 else 3  # Увеличиваем скорость прокрутки
                emoji_canvas.yview_scroll(delta, "units")

        def _on_enter(event):
            event.widget.bind("<MouseWheel>", _on_mousewheel)

        def _on_leave(event):
            event.widget.unbind("<MouseWheel>")

        # Привязываем события к canvas
        emoji_canvas.bind("<Enter>", _on_enter)
        emoji_canvas.bind("<Leave>", _on_leave)
        
        # Привязываем события к внутреннему фрейму
        emoji_inner.bind("<Enter>", _on_enter)
        emoji_inner.bind("<Leave>", _on_leave)
        
        # Привязываем события к каждой кнопке
        for child in emoji_inner.winfo_children():
            child.bind("<Enter>", _on_enter)
            child.bind("<Leave>", _on_leave)
        
        # Кнопки преобразования
        convert_frame = ttk.Frame(self.window)
        convert_frame.pack(pady=10)
        
        ttk.Button(convert_frame, text="⬆️ Декодировать", width=15,
                  command=lambda: self.convert_text("decode")).pack(side=tk.LEFT, padx=5)
        ttk.Button(convert_frame, text="⬇️ Кодировать", width=15,
                  command=lambda: self.convert_text("encode")).pack(side=tk.LEFT, padx=5)
        
        # Поле с результатом
        result_frame = ttk.LabelFrame(self.window, text="Результат", padding=10)
        result_frame.pack(fill=tk.X, padx=10, pady=5)
        
        result_btn_frame = ttk.Frame(result_frame)
        result_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(result_btn_frame, text="Вставить из буфера", 
                  command=lambda: self.paste_text(self.result_text)).pack(side=tk.LEFT, padx=5)
        ttk.Button(result_btn_frame, text="Копировать в буфер", 
                  command=lambda: self.copy_from_text(self.result_text)).pack(side=tk.LEFT, padx=5)
        ttk.Button(result_btn_frame, text="Очистить", 
                  command=lambda: self.clear_text(self.result_text)).pack(side=tk.LEFT, padx=5)
        
        self.result_text = tk.Text(result_frame, height=5, wrap=tk.WORD, font=self.default_font)
        self.result_text.pack(fill=tk.X)
        
    def paste_text(self, text_widget):
        try:
            text = self.window.clipboard_get()
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", text)
        except:
            self.show_toast("Буфер обмена пуст!")
        
    def insert_emoji(self, emoji):
        self.text_input.insert(tk.INSERT, emoji)
        
    def convert_text(self, mode):
        if mode == "encode":
            text = self.text_input.get("1.0", tk.END).strip()
            result = urllib.parse.quote(text)
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert("1.0", result)
        else:
            text = self.result_text.get("1.0", tk.END).strip()
            try:
                # Убираем все % из строки
                hex_str = text.replace('%', '')
                # Преобразуем в bytes и декодируем
                decoded = bytes.fromhex(hex_str).decode('utf-8')
                
                self.text_input.delete("1.0", tk.END)
                self.text_input.insert("1.0", decoded)
            except Exception as e:
                self.show_toast(f"Ошибка декодирования: {str(e)}")
                self.text_input.delete("1.0", tk.END)
                self.text_input.insert("1.0", text)
        
    def copy_from_text(self, text_widget):
        text = text_widget.get("1.0", tk.END).strip()
        if text:
            pyperclip.copy(text)
            self.show_toast("Скопировано в буфер обмена!")
        else:
            self.show_toast("Нет текста для копирования!")
        
    def clear_text(self, text_widget):
        text_widget.delete("1.0", tk.END)
        
    def show_toast(self, message):
        ToastNotification(message)
        
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = URLEncoder()
    app.run() 