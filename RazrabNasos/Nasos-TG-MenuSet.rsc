# ===== NASOS TELEGRAM MENU SET =====
# Исполнительный скрипт установки меню Telegram бота
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 22 июня 2025
# Версия: 1.0

# Объявление глобальных переменных
:global BotToken; :global TgMessage
:global MsgMenuStop; :global MsgMenuStatus; :global MsgMenuStart5; :global MsgMenuStart10; :global MsgMenuStart30; :global MsgMenuStart60; :global MsgMenuStart120; :global MsgMenuShow

:set TgMessage "NASOS TELEGRAM MENU SET"
/system script run Nasos-TG-SendMessage

:log warning "TG-MenuSet: Запуск установки меню Telegram бота"

# Проверка инициализации BotToken
:if ([:len $BotToken] = 0) do={
    :log error "TG-MenuSet: BotToken не инициализирован"
} else={
    # Установка значений по умолчанию для описаний команд
    :if ([:len $MsgMenuStop] = 0) do={ :set MsgMenuStop "Stop system" }
    :if ([:len $MsgMenuStatus] = 0) do={ :set MsgMenuStatus "System status" }
    :if ([:len $MsgMenuStart5] = 0) do={ :set MsgMenuStart5 "Start 5 min" }
    :if ([:len $MsgMenuStart10] = 0) do={ :set MsgMenuStart10 "Start 10 min" }
    :if ([:len $MsgMenuStart30] = 0) do={ :set MsgMenuStart30 "Start 30 min" }
    :if ([:len $MsgMenuStart60] = 0) do={ :set MsgMenuStart60 "Start 60 min" }
    :if ([:len $MsgMenuStart120] = 0) do={ :set MsgMenuStart120 "Start 120 min" }
    :if ([:len $MsgMenuShow] = 0) do={ :set MsgMenuShow "Show menu" }

    # Формирование команд меню из глобальных переменных
    :local menuCommands ("commands=[{\"command\":\"stop\",\"description\":\"" . $MsgMenuStop . "\"},{\"command\":\"status\",\"description\":\"" . $MsgMenuStatus . "\"},{\"command\":\"start5\",\"description\":\"" . $MsgMenuStart5 . "\"},{\"command\":\"start10\",\"description\":\"" . $MsgMenuStart10 . "\"},{\"command\":\"start30\",\"description\":\"" . $MsgMenuStart30 . "\"},{\"command\":\"start60\",\"description\":\"" . $MsgMenuStart60 . "\"},{\"command\":\"start120\",\"description\":\"" . $MsgMenuStart120 . "\"},{\"command\":\"menu\",\"description\":\"" . $MsgMenuShow . "\"}]")

    # Установка меню для всех scope с задержками между вызовами

    # 1. Установка меню (default)
    :log info "TG-MenuSet: Установка меню (default)"
    :local menuUrl ("https://api.telegram.org/bot" . $BotToken . "/setMyCommands\?scope={\"type\":\"default\"}")
    /tool fetch url=$menuUrl http-method=post http-data=$menuCommands keep-result=no
    :delay 1s

    # 2. Установка меню (all_private_chats)
    :log info "TG-MenuSet: Установка меню (all_private_chats)"
    :local menuUrl ("https://api.telegram.org/bot" . $BotToken . "/setMyCommands\?scope={\"type\":\"all_private_chats\"}")
    /tool fetch url=$menuUrl http-method=post http-data=$menuCommands keep-result=no
    :delay 1s

    # 3. Установка меню (all_group_chats)
    :log info "TG-MenuSet: Установка меню (all_group_chats)"
    :local menuUrl ("https://api.telegram.org/bot" . $BotToken . "/setMyCommands\?scope={\"type\":\"all_group_chats\"}")
    /tool fetch url=$menuUrl http-method=post http-data=$menuCommands keep-result=no

    :log warning "TG-MenuSet: Установка меню завершена для всех областей видимости"
}

# Очистка использованных переменных
:set TgMessage ""

:log info "TG-MenuSet: Завершение работы"