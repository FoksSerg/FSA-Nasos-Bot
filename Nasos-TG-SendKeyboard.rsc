# ===== NASOS TELEGRAM SEND KEYBOARD =====
# Исполнительный скрипт отправки сообщений с inline клавиатурой
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 22 июня 2025
# Версия: 1.0

# Объявление глобальных переменных
:global BotToken; :global ChatId; :global TgMessage; :global TgKeyboardType

:log info "TG-SendKeyboard: Запуск отправки сообщения с клавиатурой"

# Проверка инициализации переменных
:local canSend 1

:if ([:len $BotToken] = 0) do={
    :log error "TG-SendKeyboard: BotToken не инициализирован"
    :set canSend 0
}

:if ([:len $ChatId] = 0) do={
    :log error "TG-SendKeyboard: ChatId не инициализирован"
    :set canSend 0
}

:if ([:len $TgMessage] = 0) do={
    :log error "TG-SendKeyboard: Сообщение не задано"
    :set canSend 0
}

# Отправка сообщения с клавиатурой только при корректной инициализации
:if ($canSend = 1) do={
    # Определение типа клавиатуры
    :local keyboardType "main"
    :if ([:len $TgKeyboardType] > 0) do={
        :set keyboardType $TgKeyboardType
    }
    
    # Формирование inline клавиатуры в зависимости от типа
    :local inlineKeyboard ""
    
    :if ($keyboardType = "main") do={
        # Основная клавиатура управления
        :set inlineKeyboard "{\"inline_keyboard\":[[{\"text\":\"🔴 Stop\",\"callback_data\":\"stop\"},{\"text\":\"📊 Status\",\"callback_data\":\"status\"}],[{\"text\":\"⏰ 5 min\",\"callback_data\":\"start5\"},{\"text\":\"⏰ 10 min\",\"callback_data\":\"start10\"}],[{\"text\":\"⏰ 30 min\",\"callback_data\":\"start30\"},{\"text\":\"⏰ 60 min\",\"callback_data\":\"start60\"}],[{\"text\":\"⏰ 120 min\",\"callback_data\":\"start120\"},{\"text\":\"📋 Menu\",\"callback_data\":\"menu\"}]]}"
    }
    
    :if ($keyboardType = "confirm") do={
        # Клавиатура подтверждения
        :set inlineKeyboard "{\"inline_keyboard\":[[{\"text\":\"✅ Yes\",\"callback_data\":\"confirm_yes\"},{\"text\":\"❌ No\",\"callback_data\":\"confirm_no\"}]]}"
    }
    
    :if ($keyboardType = "time") do={
        # Клавиатура выбора времени
        :set inlineKeyboard "{\"inline_keyboard\":[[{\"text\":\"5 min\",\"callback_data\":\"time_5\"},{\"text\":\"10 min\",\"callback_data\":\"time_10\"},{\"text\":\"15 min\",\"callback_data\":\"time_15\"}],[{\"text\":\"30 min\",\"callback_data\":\"time_30\"},{\"text\":\"60 min\",\"callback_data\":\"time_60\"},{\"text\":\"120 min\",\"callback_data\":\"time_120\"}]]}"
    }
    
    # Формирование POST данных для отправки
    :local postData ("chat_id=" . $ChatId . "&text=" . $TgMessage . "&reply_markup=" . $inlineKeyboard)
    
    # Формирование URL для отправки сообщения
    :local apiUrl ("https://api.telegram.org/bot" . $BotToken . "/sendMessage")
    :log info ("TG-SendKeyboard: Отправка сообщения с клавиатурой типа: " . $keyboardType)
    
    # Отправка сообщения с клавиатурой
    /tool fetch url=$apiUrl http-method=post http-data=$postData keep-result=no
    :log info "TG-SendKeyboard: Сообщение с клавиатурой отправлено успешно"
} else={
    :log error "TG-SendKeyboard: Отправка сообщения прервана из-за ошибок инициализации"
}

# Очистка использованных переменных
:set TgMessage ""
:set TgKeyboardType ""

:log info "TG-SendKeyboard: Завершение работы" 