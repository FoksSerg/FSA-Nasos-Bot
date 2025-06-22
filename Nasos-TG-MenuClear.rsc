# ===== NASOS TELEGRAM MENU CLEAR =====
# Исполнительный скрипт очистки меню Telegram бота
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 22 июня 2025
# Версия: 1.0

# Объявление глобальных переменных
:global BotToken
:global TgMessage

:set TgMessage "NASOS TELEGRAM MENU CLEAR"
/system script run Nasos-TG-SendMessage

:log warning "TG-MenuClear: Запуск очистки меню Telegram бота"

# Проверка инициализации BotToken
:if ([:len $BotToken] = 0) do={
    :log error "TG-MenuClear: BotToken не инициализирован"
} else={
    # Очистка меню для всех scope с задержками между вызовами

    # 1. Очистка меню (default)
    :log info "TG-MenuClear: Очистка меню (default)"
    :local clearMenuUrl ("https://api.telegram.org/bot" . $BotToken . "/deleteMyCommands\?scope={\"type\":\"default\"}");
    /tool fetch url=$clearMenuUrl http-method=post keep-result=no;
    :delay 1s

    # 2. Очистка меню (all_private_chats)
    :log info "TG-MenuClear: Очистка меню (all_private_chats)"
    :local clearMenuUrl ("https://api.telegram.org/bot" . $BotToken . "/deleteMyCommands\?scope={\"type\":\"all_private_chats\"}");
    /tool fetch url=$clearMenuUrl http-method=post keep-result=no;
    :delay 1s

    # 3. Очистка меню (all_group_chats)
    :log info "TG-MenuClear: Очистка меню (all_group_chats)"
    :local clearMenuUrl ("https://api.telegram.org/bot" . $BotToken . "/deleteMyCommands\?scope={\"type\":\"all_group_chats\"}");
    /tool fetch url=$clearMenuUrl http-method=post keep-result=no;

    :log warning "TG-MenuClear: Очистка меню завершена для всех областей видимости"
}

# Очистка использованных переменных
:set TgMessage ""

:log info "TG-MenuClear: Завершение работы"