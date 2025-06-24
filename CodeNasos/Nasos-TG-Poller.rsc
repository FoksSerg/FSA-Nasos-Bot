:global BotToken
:global ChatId
:global LastUpdateId
:global TgLastCommand
:global TgCommandTime
:global TgPollStatus
:global TgPollError
:global TgPollHeartbeat
:global TgStartMinutes
:if ([:len $BotToken] = 0 || [:len $ChatId] = 0) do={
:set TgPollStatus "error"
:set TgPollError "Не заданы BotToken или ChatId"
:log error ("TG-Poller: " . $TgPollError)
:return false
}
:if ([:typeof $LastUpdateId] = "nothing" || [:len $LastUpdateId] = 0) do={
:set LastUpdateId 1
}
:local pollSuccess false
:local content ""
:local errorMessage ""
:do {
:local getUrl ("https://api.telegram.org/bot" . $BotToken . "/getUpdates?limit=5&offset=" . $LastUpdateId)
:local updates [/tool fetch url=$getUrl as-value output=user]
:set content ($updates->"data")
:if ([:len $content] > 10) do={
:set pollSuccess true
} else={
:set pollSuccess true
}
} on-error={
:set errorMessage "Ошибка запроса к Telegram API"
:log error ("TG-Poller: " . $errorMessage)
}
:if ($pollSuccess) do={
:set TgPollStatus "ok"
:set TgPollError ""
:set TgPollHeartbeat [/system clock get time]
:if ([:len $content] > 10) do={
:local updateIdPos [:find $content "\"update_id\":"]
:if ([:len $updateIdPos] > 0) do={
:local idStart ($updateIdPos + 12)
:local idEnd [:find $content "," $idStart]
:local newUpdateId [:pick $content $idStart $idEnd]
:set LastUpdateId ($newUpdateId + 1)
}
:local detectedCommand ""
:if ([:len [:find $content "\"/stop\""]] > 0 || [:len [:find $content "\"stop\""]] > 0) do={
:set detectedCommand "stop"
}
:if ([:len [:find $content "\"/status\""]] > 0 || [:len [:find $content "\"status\""]] > 0) do={
:set detectedCommand "status"
}
:if ([:len [:find $content "\"/menu\""]] > 0 || [:len [:find $content "\"menu\""]] > 0) do={
:set detectedCommand "menu"
}
:if ([:len $detectedCommand] = 0) do={
:local startPos1 [:find $content "\"/start"]
:local startPos2 [:find $content "\"start"]
:local startPos 0
:local hasSpace false
:if ([:len $startPos1] > 0) do={
:set startPos ($startPos1 + 7)
:local nextChar [:pick $content $startPos ($startPos + 1)]
:if ($nextChar = " ") do={
:set hasSpace true
:set startPos ($startPos + 1)
}
}
:if ([:len $startPos2] > 0 && [:len $startPos1] = 0) do={
:set startPos ($startPos2 + 6)
:local nextChar [:pick $content $startPos ($startPos + 1)]
:if ($nextChar = " ") do={
:set hasSpace true
:set startPos ($startPos + 1)
}
}
:if ($startPos > 0) do={
:local endPos [:find $content "\"" $startPos]
:if ([:len $endPos] > 0) do={
:local minutesStr [:pick $content $startPos $endPos]
:if ([:len $minutesStr] > 0 && [:len $minutesStr] < 6) do={
:local minutes [:tonum $minutesStr]
:if ($minutes >= -999 && $minutes <= 999) do={
:set detectedCommand "start"
:set TgStartMinutes $minutes
}
}
}
}
}
:if ([:len $detectedCommand] > 0) do={
:set TgLastCommand $detectedCommand
:set TgCommandTime [/system clock get time]
:log warning ("Команда: " . $detectedCommand)
}
}
} else={
:set TgPollStatus "error"
:set TgPollError $errorMessage
:log error ("TG-Poller: Опрос завершен с ошибкой: " . $errorMessage)
}
