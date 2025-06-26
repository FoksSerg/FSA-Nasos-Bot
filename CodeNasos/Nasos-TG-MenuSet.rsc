:global BotToken; :global TgMessage;
:global MsgMenuStop; :global MsgMenuStatus; :global MsgMenuStart5; :global MsgMenuStart10; :global MsgMenuStart30; :global MsgMenuStart60; :global MsgMenuStart120; :global MsgMenuShow;
:set TgMessage "NASOS TELEGRAM MENU SET";
/system script run Nasos-TG-SendMessage;
:log warning "TG-MenuSet: Запуск установки меню Telegram бота";
:if ([:len $BotToken] = 0) do={
:log error "TG-MenuSet: BotToken не инициализирован";
} else={
:if ([:len $MsgMenuStop] = 0) do={ :set MsgMenuStop "Stop system" }
:if ([:len $MsgMenuStatus] = 0) do={ :set MsgMenuStatus "System status" }
:if ([:len $MsgMenuStart5] = 0) do={ :set MsgMenuStart5 "Start 5 min" }
:if ([:len $MsgMenuStart10] = 0) do={ :set MsgMenuStart10 "Start 10 min" }
:if ([:len $MsgMenuStart30] = 0) do={ :set MsgMenuStart30 "Start 30 min" }
:if ([:len $MsgMenuStart60] = 0) do={ :set MsgMenuStart60 "Start 60 min" }
:if ([:len $MsgMenuStart120] = 0) do={ :set MsgMenuStart120 "Start 120 min" }
:if ([:len $MsgMenuShow] = 0) do={ :set MsgMenuShow "Show menu" }
:local menuCommands ("commands=[{\"command\":\"stop\",\"description\":\"" . $MsgMenuStop . "\"},{\"command\":\"status\",\"description\":\"" . $MsgMenuStatus . "\"},{\"command\":\"start5\",\"description\":\"" . $MsgMenuStart5 . "\"},{\"command\":\"start10\",\"description\":\"" . $MsgMenuStart10 . "\"},{\"command\":\"start30\",\"description\":\"" . $MsgMenuStart30 . "\"},{\"command\":\"start60\",\"description\":\"" . $MsgMenuStart60 . "\"},{\"command\":\"start120\",\"description\":\"" . $MsgMenuStart120 . "\"},{\"command\":\"menu\",\"description\":\"" . $MsgMenuShow . "\"}]");
:log info "TG-MenuSet: Установка меню (default)";
:local menuUrl ("https://api.telegram.org/bot" . $BotToken . "/setMyCommands\?scope={\"type\":\"default\"}");
/tool fetch url=$menuUrl http-method=post http-data=$menuCommands keep-result=no;
:delay 1s;
:log info "TG-MenuSet: Установка меню (all_private_chats)";
:local menuUrl ("https://api.telegram.org/bot" . $BotToken . "/setMyCommands\?scope={\"type\":\"all_private_chats\"}");
/tool fetch url=$menuUrl http-method=post http-data=$menuCommands keep-result=no;
:delay 1s;
:log info "TG-MenuSet: Установка меню (all_group_chats)";
:local menuUrl ("https://api.telegram.org/bot" . $BotToken . "/setMyCommands\?scope={\"type\":\"all_group_chats\"}");
/tool fetch url=$menuUrl http-method=post http-data=$menuCommands keep-result=no;
:log warning "TG-MenuSet: Установка меню завершена для всех областей видимости";
}
:set TgMessage "";
:log info "TG-MenuSet: Завершение работы";
