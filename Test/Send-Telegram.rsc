:global BotToken
:global ChatId
:global TelegramSendStatus
:global TelegramSendError
:global TelegramSendMsg

:set TelegramSendStatus "started"
:set TelegramSendError ""
:local msg $TelegramSendMsg
:local url ("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $msg)

/tool fetch url=$url keep-result=no

:set TelegramSendStatus "done"
:set TelegramSendError ""