# ===== NASOS TELEGRAM SEND MESSAGE =====
# Исполнительный скрипт отправки сообщений в Telegram
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 22 июня 2025
# Версия: 1.0

# Объявление глобальных переменных
:global BotToken; :global ChatId; :global TgMessage

:log info "TG-SendMessage: Запуск отправки сообщения"

# Проверка инициализации переменных
:local canSend 1

:if ([:len $BotToken] = 0) do={
    :log error "TG-SendMessage: BotToken не инициализирован"
    :set canSend 0
}

:if ([:len $ChatId] = 0) do={
    :log error "TG-SendMessage: ChatId не инициализирован"
    :set canSend 0
}

:if ([:len $TgMessage] = 0) do={
    :log error "TG-SendMessage: Сообщение не задано"
    :set canSend 0
}

# Отправка сообщения только при корректной инициализации
:if ($canSend = 1) do={
    # Формирование URL для отправки сообщения
    :local apiUrl ("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $TgMessage)
    :log info ("TG-SendMessage: Отправка сообщения: " . $TgMessage)
    # Отправка сообщения
    /tool fetch url=$apiUrl http-method=post keep-result=no
    :log info "TG-SendMessage: Сообщение отправлено успешно"
} else={
    :log error "TG-SendMessage: Отправка сообщения прервана из-за ошибок инициализации"
}

# Очистка использованных переменных
:set TgMessage ""

:log info "TG-SendMessage: Завершение работы"