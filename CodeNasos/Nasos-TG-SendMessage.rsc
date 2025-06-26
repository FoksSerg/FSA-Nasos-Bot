:global BotToken; :global ChatId; :global TgMessage;
:log info "TG-SendMessage: Запуск отправки сообщения";
:local canSend 1;
:if ([:len $BotToken] = 0) do={
:log error "TG-SendMessage: BotToken не инициализирован";
:set canSend 0;
}
:if ([:len $ChatId] = 0) do={
:log error "TG-SendMessage: ChatId не инициализирован";
:set canSend 0;
}
:if ([:len $TgMessage] = 0) do={
:log error "TG-SendMessage: Сообщение не задано";
:set canSend 0;
}
:if ($canSend = 1) do={
:local apiUrl ("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $TgMessage);
:log info ("TG-SendMessage: Отправка сообщения: " . $TgMessage);
/tool fetch url=$apiUrl http-method=post keep-result=no;
:log info "TG-SendMessage: Сообщение отправлено успешно";
} else={
:log error "TG-SendMessage: Отправка сообщения прервана из-за ошибок инициализации";
}
:set TgMessage "";
:log info "TG-SendMessage: Завершение работы";
