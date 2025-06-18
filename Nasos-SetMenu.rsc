# Скрипт установки меню для Telegram бота
:global BotToken;
:global MsgMenuStop;
:global MsgMenuStatus;
:global MsgMenuStart5;
:global MsgMenuStart10;
:global MsgMenuStart30;
:global MsgMenuStart60;
:global MsgMenuStart120;
:global MsgMenuShow;

# Очистка старого меню для всех scope
:local clearMenuUrl ("https://api.telegram.org/bot" . $BotToken . "/deleteMyCommands\?scope={\"type\":\"default\"}");
/tool fetch url=$clearMenuUrl http-method=post keep-result=no;
:delay 1s;
:local clearMenuUrl ("https://api.telegram.org/bot" . $BotToken . "/deleteMyCommands\?scope={\"type\":\"all_private_chats\"}");
/tool fetch url=$clearMenuUrl http-method=post keep-result=no;
:delay 1s;
:local clearMenuUrl ("https://api.telegram.org/bot" . $BotToken . "/deleteMyCommands\?scope={\"type\":\"all_group_chats\"}");
/tool fetch url=$clearMenuUrl http-method=post keep-result=no;
:delay 2s;

# Формирование команд меню из глобальных переменных
:local menuCommands ("commands=[{\"command\":\"stop\",\"description\":\"" . $MsgMenuStop . "\"},{\"command\":\"status\",\"description\":\"" . $MsgMenuStatus . "\"},{\"command\":\"start5\",\"description\":\"" . $MsgMenuStart5 . "\"},{\"command\":\"start10\",\"description\":\"" . $MsgMenuStart10 . "\"},{\"command\":\"start30\",\"description\":\"" . $MsgMenuStart30 . "\"},{\"command\":\"start60\",\"description\":\"" . $MsgMenuStart60 . "\"},{\"command\":\"start120\",\"description\":\"" . $MsgMenuStart120 . "\"},{\"command\":\"menu\",\"description\":\"" . $MsgMenuShow . "\"}]");
:log info $menuCommands

# Установка нового меню для всех scope
:local menuUrl ("https://api.telegram.org/bot" . $BotToken . "/setMyCommands\?scope={\"type\":\"default\"}");
/tool fetch url=$menuUrl http-method=post http-data=$menuCommands keep-result=no;
:delay 1s;
:local menuUrl ("https://api.telegram.org/bot" . $BotToken . "/setMyCommands\?scope={\"type\":\"all_private_chats\"}");
/tool fetch url=$menuUrl http-method=post http-data=$menuCommands keep-result=no;
:delay 1s;
:local menuUrl ("https://api.telegram.org/bot" . $BotToken . "/setMyCommands\?scope={\"type\":\"all_group_chats\"}");
/tool fetch url=$menuUrl http-method=post http-data=$menuCommands keep-result=no;

:log info "Насос - Меню Telegram установлено"; 