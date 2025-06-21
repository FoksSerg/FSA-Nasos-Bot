:global BotToken
:global ChatId
:global TelegramSendStatus
:global TelegramSendError
:global TelegramSendMsg
:global TelegramSendUrl
:global TelegramSendMethod
:global TelegramSendData

:set TelegramSendStatus "started"
:set TelegramSendError ""

# Логирование параметров для отладки
:if ([:len $TelegramSendMsg] > 0) do={
    :log info ("SendTG - Отправка сообщения: " . $TelegramSendMsg)
    :local msg $TelegramSendMsg
    :local url ("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $msg)
    /tool fetch url=$url keep-result=no
} else={
    :if ([:len $TelegramSendUrl] > 0) do={
        :log info ("SendTG - Выполнение запроса: " . $TelegramSendUrl)
        :log info ("SendTG - Метод: " . $TelegramSendMethod . ", Данные: " . [:len $TelegramSendData] . " символов")
        /tool fetch url=$TelegramSendUrl http-method=$TelegramSendMethod http-data=$TelegramSendData keep-result=no
    } else={
        :log error "SendTG - ОШИБКА: Нет данных для отправки (TelegramSendMsg и TelegramSendUrl пусты)"
        :set TelegramSendError "No data to send"
    }
}

:set TelegramSendStatus "done"
:set TelegramSendError ""