:global BotToken
:global TgMessage
:set TgMessage "NASOS TELEGRAM MENU CLEAR"
/system script run Nasos-TG-SendMessage
:log warning "TG-MenuClear: Запуск очистки меню Telegram бота"
:if ([:len $BotToken] = 0) do={
:log error "TG-MenuClear: BotToken не инициализирован"
} else={
:log info "TG-MenuClear: Очистка меню (default)"
:local clearMenuUrl ("https://api.telegram.org/bot" . $BotToken . "/deleteMyCommands\?scope={\"type\":\"default\"}");
/tool fetch url=$clearMenuUrl http-method=post keep-result=no;
:delay 1s
:log info "TG-MenuClear: Очистка меню (all_private_chats)"
:local clearMenuUrl ("https://api.telegram.org/bot" . $BotToken . "/deleteMyCommands\?scope={\"type\":\"all_private_chats\"}");
/tool fetch url=$clearMenuUrl http-method=post keep-result=no;
:delay 1s
:log info "TG-MenuClear: Очистка меню (all_group_chats)"
:local clearMenuUrl ("https://api.telegram.org/bot" . $BotToken . "/deleteMyCommands\?scope={\"type\":\"all_group_chats\"}");
/tool fetch url=$clearMenuUrl http-method=post keep-result=no;
:log warning "TG-MenuClear: Очистка меню завершена для всех областей видимости"
}
:set TgMessage ""
:log info "TG-MenuClear: Завершение работы"
