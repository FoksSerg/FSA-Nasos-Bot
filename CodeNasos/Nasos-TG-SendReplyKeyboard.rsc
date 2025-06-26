:global BotToken; :global ChatId; :global TgMessage; :global TgKeyboardType;
:log info "TG-SendReplyKeyboard: Запуск отправки сообщения с Reply клавиатурой";
:local canSend 1;
:if ([:len $BotToken] = 0) do={
:log error "TG-SendReplyKeyboard: BotToken не инициализирован";
:set canSend 0;
}
:if ([:len $ChatId] = 0) do={
:log error "TG-SendReplyKeyboard: ChatId не инициализирован";
:set canSend 0;
}
:if ([:len $TgMessage] = 0) do={
:log error "TG-SendReplyKeyboard: Сообщение не задано";
:set canSend 0;
}
:if ($canSend = 1) do={
:local keyboardType "main";
:if ([:len $TgKeyboardType] > 0) do={
:set keyboardType $TgKeyboardType;
}
:local replyKeyboard "";
:if ($keyboardType = "main") do={
:set replyKeyboard "{\"keyboard\":[[\"🔴 Stop\",\"📊 Status\"],[\"⏰ Start 5\",\"⏰ Start 10\"],[\"⏰ Start 30\",\"⏰ Start 60\"],[\"⏰ Start 120\",\"📋 Menu\"]],\"resize_keyboard\":true,\"persistent\":true}";
}
:if ($keyboardType = "simple") do={
:set replyKeyboard "{\"keyboard\":[[\"Stop\",\"Status\",\"Start\"]],\"resize_keyboard\":true,\"persistent\":true}";
}
:if ($keyboardType = "time") do={
:set replyKeyboard "{\"keyboard\":[[\"5 min\",\"10 min\",\"15 min\"],[\"30 min\",\"60 min\",\"120 min\"]],\"resize_keyboard\":true,\"one_time_keyboard\":true}";
}
:if ($keyboardType = "hide") do={
:set replyKeyboard "{\"remove_keyboard\":true}";
}
:local postData ("chat_id=" . $ChatId . "&text=" . $TgMessage . "&reply_markup=" . $replyKeyboard);
:local apiUrl ("https://api.telegram.org/bot" . $BotToken . "/sendMessage");
:log info ("TG-SendReplyKeyboard: Отправка сообщения с Reply клавиатурой типа: " . $keyboardType);
/tool fetch url=$apiUrl http-method=post http-data=$postData keep-result=no;
:log info "TG-SendReplyKeyboard: Сообщение с Reply клавиатурой отправлено успешно";
} else={
:log error "TG-SendReplyKeyboard: Отправка сообщения прервана из-за ошибок инициализации";
}
:set TgMessage "";
:set TgKeyboardType "";
:log info "TG-SendReplyKeyboard: Завершение работы";
