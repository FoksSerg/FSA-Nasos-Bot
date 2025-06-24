:global NasosInitStatus; :global BotToken; :global ChatId; :global PoeMainInterface; :global NewDuration
:global PoeActiveTimer; :global PoeStartTime; :global PoeTimerName; :global LastStopTime; :global LastWorkDuration; :global ExpectedStopTime
:global MsgSysStarted; :global MsgSysError; :global MsgPumpOn; :global MsgPumpAlreadyOn; :global MsgPumpAutoStop; :global MsgPumpStoppedByCmd; :global MsgPumpStoppedTimeReduced
:global MsgTimeWorked; :global MsgTimeMin; :global MsgTimeSec; :global MsgTimeReduced; :global MsgTimeWorkedTemplate; :global MsgTimeAlreadyWorkedTemplate; :global MsgTimeAlreadyWorkedTranslit
:global MsgNewLine; :global MsgHeader; :global MsgStatusHeader; :global MsgStatusCurrent; :global MsgTimeRemaining; :global MsgTimeExpectedTotal; :global MsgTimeWorkedHeader; :global MsgTimeStoppedAt
:global MsgPumpStartedFor; :global MsgStopCmdTemplate; :global MsgPumpAlreadyStopped; :global MsgTimeSinceStop; :global MsgErrorNoActiveTimer
:global InputSeconds; :global FormattedLog; :global FormattedTelegram
:global timeToSeconds do={
:local timeStr $1
:if ([:typeof $timeStr] = "nothing" || [:len $timeStr] = 0 || [:len $timeStr] < 8) do={
:return 0
}
:local hours [:pick $timeStr 0 2]
:local minutes [:pick $timeStr 3 5]
:local seconds [:pick $timeStr 6 8]
:if ([:typeof [:tonum $hours]] = "nothing" || [:typeof [:tonum $minutes]] = "nothing" || [:typeof [:tonum $seconds]] = "nothing") do={
:return 0
}
:return ($hours * 3600 + $minutes * 60 + $seconds)
}
:if ([:typeof $NasosInitStatus] = "nothing" || !$NasosInitStatus) do={
:log warning "Насос - Запуск Nasos-Init"
/system script run Nasos-Init
}
:if ([:len $BotToken] = 0 or [:len $ChatId] = 0 or [:len $PoeMainInterface] = 0) do={
:log error "Насос - КРИТИЧЕСКАЯ ОШИБКА: Обязательные глобальные переменные не определены!"
}
:local sendTelegram do={
:local token $1
:local chatId $2
:local message $3
:local url "https://api.telegram.org/bot$token/sendMessage"
/tool fetch url=$url http-method=post http-data="chat_id=$chatId&text=$message" keep-result=no
}
:if ([:len [/interface ethernet find name=$PoeMainInterface]] = 0) do={
:log error "Насос - POE интерфейс не найден"
$sendTelegram $BotToken $ChatId ($MsgSysError . "POE%20%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D1%84%D0%B5%D0%B9%D1%81%20%D0%BD%D0%B5%20%D0%BD%D0%B0%D0%B9%D0%B4%D0%B5%D0%BD")
} else={
:local currentPoeStatus [/interface ethernet get [find name=$PoeMainInterface] poe-out]
:if ([:len $NewDuration] = 0) do={
:log info "Насос - Длительность не установлена"
} else={
:if ([:typeof $NewDuration] = "num") do={
:local poeStatus [/interface ethernet get [find name=$PoeMainInterface] poe-out]
:if ($NewDuration = 0) do={
:if ($poeStatus != "off") do={
/interface ethernet poe set $PoeMainInterface poe-out=off
:log warning "Насос - POE ФИЗИЧЕСКИ ОТКЛЮЧЕН"
:local workTimeMsg ""
:if ([:len $PoeStartTime] > 0) do={
:local currentTime [/system clock get time]
:local startSeconds [$timeToSeconds $PoeStartTime]
:local currentSeconds [$timeToSeconds $currentTime]
:local workSeconds ($currentSeconds - $startSeconds)
:if ($workSeconds < 0) do={
:set workSeconds ($workSeconds + 86400)
}
:set InputSeconds $workSeconds
/system script run Nasos-TimeUtils
:set workTimeMsg (" " . $FormattedLog)
}
:set LastStopTime [/system clock get time]
:local logMsg "Насос - НАСОС ОСТАНОВЛЕН ПО КОМАНДЕ"
:set logMsg ($logMsg . $workTimeMsg)
:log warning $logMsg
:local telegramWorkMsg ""
:if ([:len $PoeStartTime] > 0) do={
:local currentTime [/system clock get time]
:local startSeconds [$timeToSeconds $PoeStartTime]
:local currentSeconds [$timeToSeconds $currentTime]
:local workSeconds ($currentSeconds - $startSeconds)
:if ($workSeconds < 0) do={
:set workSeconds ($workSeconds + 86400)
}
:set InputSeconds $workSeconds
/system script run Nasos-TimeUtils
:set telegramWorkMsg ($MsgTimeWorkedHeader . " " . $FormattedTelegram)
:set LastWorkDuration $workSeconds
}
:local stopTime [/system clock get time]
:local telegramMsg ($MsgStatusHeader . " " . $MsgPumpStoppedByCmd . $MsgNewLine . $telegramWorkMsg . $MsgNewLine . $MsgTimeStoppedAt . $stopTime)
$sendTelegram $BotToken $ChatId $telegramMsg
:if ([:len $PoeActiveTimer] > 0) do={
:if ([:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
/system scheduler remove [find name=$PoeActiveTimer]
:log warning ("Насос - Удален активный таймер: " . $PoeActiveTimer)
}
:set PoeActiveTimer ""
}
:if ([:len [/system scheduler find name=$PoeTimerName]] > 0) do={
/system scheduler remove [find name=$PoeTimerName]
:log warning ("Насос - Принудительно удален таймер: " . $PoeTimerName)
}
:set PoeStartTime ""
:set ExpectedStopTime ""
:set NewDuration ""
} else={
:local timeSinceStopMsg ""
:if ([:len $LastStopTime] > 0) do={
:local currentTime [/system clock get time]
:local stopSeconds [$timeToSeconds $LastStopTime]
:local currentSeconds [$timeToSeconds $currentTime]
:local timeSinceStop ($currentSeconds - $stopSeconds)
:if ($timeSinceStop < 0) do={
:set timeSinceStop ($timeSinceStop + 86400)
}
:local stopMinutes ($timeSinceStop / 60)
:local stopSecondsRem ($timeSinceStop - ($stopMinutes * 60))
:set timeSinceStopMsg ($MsgTimeSinceStop . " " . [:tostr $stopMinutes] . $MsgTimeMin . [:tostr $stopSecondsRem] . $MsgTimeSec)
}
:log warning ("Насос - НАСОС УЖЕ ОТКЛЮЧЕН" . $timeSinceStopMsg)
:local telegramMsg ($MsgStatusHeader . " " . $MsgPumpAlreadyStopped . $MsgNewLine . $timeSinceStopMsg)
$sendTelegram $BotToken $ChatId $telegramMsg
:set NewDuration ""
}
} else={
:if ($NewDuration < 0) do={
:if ([:len $PoeActiveTimer] > 0) do={
:local workSeconds 0
:local remainingSeconds 0
:local currentTime [/system clock get time]
:local currentSeconds [$timeToSeconds $currentTime]
:if ([:len $PoeStartTime] > 0) do={
:local startSeconds [$timeToSeconds $PoeStartTime]
:set workSeconds ($currentSeconds - $startSeconds)
:if ($workSeconds < 0) do={
:set workSeconds ($workSeconds + 86400)
}
}
:if ([:len $ExpectedStopTime] > 0) do={
:local stopSeconds [$timeToSeconds $ExpectedStopTime]
:set remainingSeconds ($stopSeconds - $currentSeconds)
:if ($remainingSeconds < 0) do={
:set remainingSeconds ($remainingSeconds + 86400)
}
}
:local newRemainingSeconds ($remainingSeconds + $NewDuration)
:if ($newRemainingSeconds <= 0) do={
:local workTimeMsg ""
:if ([:len $PoeStartTime] > 0) do={
:local currentTime [/system clock get time]
:local startSeconds [$timeToSeconds $PoeStartTime]
:local currentSeconds [$timeToSeconds $currentTime]
:local workSeconds ($currentSeconds - $startSeconds)
:if ($workSeconds < 0) do={
:set workSeconds ($workSeconds + 86400)
}
:local workMinutes ($workSeconds / 60)
:local workSecondsRem ($workSeconds - ($workMinutes * 60))
:set workTimeMsg ($MsgTimeWorkedTemplate . [:tostr $workMinutes] . $MsgTimeMin . [:tostr $workSecondsRem] . $MsgTimeSec)
}
$sendTelegram $BotToken $ChatId ($MsgStatusCurrent . $MsgNewLine . $MsgPumpAutoStop . $workTimeMsg)
:set LastStopTime [/system clock get time]
:set LastWorkDuration $workSeconds
:local logMsg "Насос - НАСОС ОСТАНОВЛЕН - время уменьшено"
:set logMsg ($logMsg . $workTimeMsg)
:log warning $logMsg
:local telegramWorkMsg ""
:if ([:len $PoeStartTime] > 0) do={
:local workMinutes ($workSeconds / 60)
:local workSecondsRem ($workSeconds - ($workMinutes * 60))
:set telegramWorkMsg ($MsgTimeWorkedHeader . " " . [:tostr $workMinutes] . $MsgTimeMin . [:tostr $workSecondsRem] . $MsgTimeSec)
}
:local telegramMsg ($MsgStatusHeader . " " . $MsgPumpStoppedTimeReduced . $MsgNewLine . $telegramWorkMsg)
$sendTelegram $BotToken $ChatId $telegramMsg
:if ([:len $PoeActiveTimer] > 0) do={
:if ([:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
/system scheduler remove [find name=$PoeActiveTimer]
:log warning ("Насос - Удален старый таймер: " . $PoeActiveTimer)
}
}
:if ([:len [/system scheduler find name=$PoeTimerName]] > 0) do={
/system scheduler remove [find name=$PoeTimerName]
:log warning ("Насос - Принудительно удален таймер: " . $PoeTimerName)
}
:set PoeActiveTimer ""
:set PoeStartTime ""
:set ExpectedStopTime ""
:set NewDuration ""
} else={
:local newTotalSeconds ($workSeconds + $newRemainingSeconds)
:local newIntervalHours ($newRemainingSeconds / 3600)
:local newIntervalMins (($newRemainingSeconds - ($newIntervalHours * 3600)) / 60)
:local newIntervalSecsRem ($newRemainingSeconds - ($newIntervalHours * 3600) - ($newIntervalMins * 60))
:if ($newIntervalHours < 10) do={ :set newIntervalHours ("0" . $newIntervalHours) }
:if ($newIntervalMins < 10) do={ :set newIntervalMins ("0" . $newIntervalMins) }
:if ($newIntervalSecsRem < 10) do={ :set newIntervalSecsRem ("0" . $newIntervalSecsRem) }
:local newInterval ($newIntervalHours . ":" . $newIntervalMins . ":" . $newIntervalSecsRem)
/system scheduler set [find name=$PoeActiveTimer] interval=$newInterval
:local currentTime [/system clock get time]
:local currentSeconds [$timeToSeconds $currentTime]
:local newStopSeconds (($currentSeconds + $newRemainingSeconds) % 86400)
:local stopHours ($newStopSeconds / 3600)
:local stopMins (($newStopSeconds - ($stopHours * 3600)) / 60)
:local stopSecsRem ($newStopSeconds - ($stopHours * 3600) - ($stopMins * 60))
:if ($stopHours < 10) do={ :set stopHours ("0" . $stopHours) }
:if ($stopMins < 10) do={ :set stopMins ("0" . $stopMins) }
:if ($stopSecsRem < 10) do={ :set stopSecsRem ("0" . $stopSecsRem) }
:set ExpectedStopTime ($stopHours . ":" . $stopMins . ":" . $stopSecsRem)
:local reducedSecs (0 - $NewDuration)
:set InputSeconds $reducedSecs
/system script run Nasos-TimeUtils
:local reducedTimeFormatted $FormattedTelegram
:set InputSeconds $workSeconds
/system script run Nasos-TimeUtils
:local workTimeFormatted $FormattedTelegram
:set InputSeconds $newTotalSeconds
/system script run Nasos-TimeUtils
:local totalTimeFormatted $FormattedTelegram
:log warning ($MsgTimeReduced . " " . $reducedTimeFormatted)
:log warning ($MsgTimeExpectedTotal . " " . $totalTimeFormatted)
:local telegramMsg ($MsgTimeReduced . " " . $reducedTimeFormatted . $MsgNewLine . $MsgTimeWorkedHeader . " " . $workTimeFormatted . $MsgNewLine . $MsgNewLine . $MsgTimeExpectedTotal . " " . $totalTimeFormatted)
$sendTelegram $BotToken $ChatId $telegramMsg
:set NewDuration ""
}
} else={
:log error "Насос - Нет активного таймера"
$sendTelegram $BotToken $ChatId ($MsgSysError . $MsgErrorNoActiveTimer)
:set NewDuration ""
}
} else={
:if ($NewDuration > 0) do={
:local durationMinutes ($NewDuration / 60)
:local durationSeconds ($NewDuration - ($durationMinutes * 60))
:set InputSeconds $NewDuration
/system script run Nasos-TimeUtils
:local durationFormatted $FormattedTelegram
:if ($poeStatus = "forced-on") do={
:local workTimeMsg ""
:local workSeconds 0
:if ([:len $PoeStartTime] > 0) do={
:local currentTime [/system clock get time]
:local startSeconds [$timeToSeconds $PoeStartTime]
:local currentSeconds [$timeToSeconds $currentTime]
:set workSeconds ($currentSeconds - $startSeconds)
:if ($workSeconds < 0) do={
:set workSeconds ($workSeconds + 86400)
}
:local workMinutes ($workSeconds / 60)
:local workSecondsRem ($workSeconds - ($workMinutes * 60))
:set workTimeMsg ($MsgTimeAlreadyWorkedTemplate . [:tostr $workMinutes] . $MsgTimeMin . [:tostr $workSecondsRem] . $MsgTimeSec)
}
:local logMsg ("Насос - НАСОС УЖЕ РАБОТАЕТ - будет работать еще" . " " . $durationMinutes . " минут " . $durationSeconds . " секунд")
:set logMsg ($logMsg . $workTimeMsg)
:log warning $logMsg
:local totalExpectedTime ($workSeconds + $NewDuration)
:local totalExpectedMinutes ($totalExpectedTime / 60)
:local totalExpectedSeconds ($totalExpectedTime - ($totalExpectedMinutes * 60))
:log warning ($MsgTimeExpectedTotal . " " . $totalExpectedMinutes . $MsgTimeMin . $totalExpectedSeconds . $MsgTimeSec)
:set InputSeconds $workSeconds
/system script run Nasos-TimeUtils
:local telegramWorkMsg ($MsgTimeWorkedHeader . " " . $FormattedTelegram)
:set InputSeconds $totalExpectedTime
/system script run Nasos-TimeUtils
:local telegramTotalMsg ($MsgTimeExpectedTotal . " " . $FormattedTelegram)
:local telegramMsg ($MsgStatusHeader . " " . $MsgPumpAlreadyOn . $MsgNewLine . $MsgTimeRemaining . " " . $durationFormatted . $MsgNewLine . $telegramWorkMsg . $MsgNewLine . $telegramTotalMsg)
$sendTelegram $BotToken $ChatId $telegramMsg
:local intervalHours ($NewDuration / 3600)
:local intervalMins (($NewDuration - ($intervalHours * 3600)) / 60)
:local intervalSecs ($NewDuration - ($intervalHours * 3600) - ($intervalMins * 60))
:if ($intervalHours < 10) do={ :set intervalHours ("0" . $intervalHours) }
:if ($intervalMins < 10) do={ :set intervalMins ("0" . $intervalMins) }
:if ($intervalSecs < 10) do={ :set intervalSecs ("0" . $intervalSecs) }
:local newInterval ($intervalHours . ":" . $intervalMins . ":" . $intervalSecs)
:if ([:len $PoeActiveTimer] > 0) do={
:if ([:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
/system scheduler remove [find name=$PoeActiveTimer]
:log warning ("Насос - Удален старый таймер: " . $PoeActiveTimer)
}
}
:if ([:len [/system scheduler find name=$PoeTimerName]] > 0) do={
/system scheduler remove [find name=$PoeTimerName]
:log warning ("Насос - Принудительно удален таймер: " . $PoeTimerName)
}
:local currentTime [/system clock get time]
:local currentSeconds [$timeToSeconds $currentTime]
:local stopSeconds (($currentSeconds + $NewDuration) % 86400)
:local stopHours ($stopSeconds / 3600)
:local stopMins (($stopSeconds - ($stopHours * 3600)) / 60)
:local stopSecsRem ($stopSeconds - ($stopHours * 3600) - ($stopMins * 60))
:if ($stopHours < 10) do={ :set stopHours ("0" . $stopHours) }
:if ($stopMins < 10) do={ :set stopMins ("0" . $stopMins) }
:if ($stopSecsRem < 10) do={ :set stopSecsRem ("0" . $stopSecsRem) }
:set ExpectedStopTime ($stopHours . ":" . $stopMins . ":" . $stopSecsRem)
:local timerName $PoeTimerName
/system scheduler add name=$timerName interval=$newInterval on-event=$MsgStopCmdTemplate
:set PoeActiveTimer $timerName
:log warning ("Насос - Создан новый таймер: " . $timerName . " с интервалом: " . $newInterval . ", ожидаемая остановка: " . $ExpectedStopTime)
} else={
/interface ethernet set [find name=$PoeMainInterface] poe-out=forced-on
:set PoeStartTime [/system clock get time]
:local logMsg ("Насос - НАСОС ЗАПУЩЕН на " . $durationMinutes . " минут " . $durationSeconds . " секунд")
:log warning $logMsg
:local telegramMsg ($MsgStatusHeader . " " . $MsgPumpOn . $MsgNewLine . $MsgPumpStartedFor . " " . $durationFormatted)
$sendTelegram $BotToken $ChatId $telegramMsg
:local intervalHours ($NewDuration / 3600)
:local intervalMins (($NewDuration - ($intervalHours * 3600)) / 60)
:local intervalSecs ($NewDuration - ($intervalHours * 3600) - ($intervalMins * 60))
:if ($intervalHours < 10) do={ :set intervalHours ("0" . $intervalHours) }
:if ($intervalMins < 10) do={ :set intervalMins ("0" . $intervalMins) }
:if ($intervalSecs < 10) do={ :set intervalSecs ("0" . $intervalSecs) }
:local schedulerInterval ($intervalHours . ":" . $intervalMins . ":" . $intervalSecs)
:if ([:len $PoeActiveTimer] > 0) do={
:if ([:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
/system scheduler remove [find name=$PoeActiveTimer]
:log warning ("Насос - Удален старый таймер: " . $PoeActiveTimer)
}
}
:if ([:len [/system scheduler find name=$PoeTimerName]] > 0) do={
/system scheduler remove [find name=$PoeTimerName]
:log warning ("Насос - Принудительно удален таймер: " . $PoeTimerName)
}
:local currentTime [/system clock get time]
:local currentSeconds [$timeToSeconds $currentTime]
:local stopSeconds (($currentSeconds + $NewDuration) % 86400)
:local stopHours ($stopSeconds / 3600)
:local stopMins (($stopSeconds - ($stopHours * 3600)) / 60)
:local stopSecsRem ($stopSeconds - ($stopHours * 3600) - ($stopMins * 60))
:if ($stopHours < 10) do={ :set stopHours ("0" . $stopHours) }
:if ($stopMins < 10) do={ :set stopMins ("0" . $stopMins) }
:if ($stopSecsRem < 10) do={ :set stopSecsRem ("0" . $stopSecsRem) }
:set ExpectedStopTime ($stopHours . ":" . $stopMins . ":" . $stopSecsRem)
:local timerName $PoeTimerName
/system scheduler add name=$timerName interval=$schedulerInterval on-event=$MsgStopCmdTemplate
:set PoeActiveTimer $timerName
:log warning ("Насос - Создан новый таймер: " . $timerName . " с интервалом: " . $schedulerInterval . ", ожидаемая остановка: " . $ExpectedStopTime)
}
:set NewDuration ""
}
}
}
} else={
:log error "Насос - Длительность должна быть числом"
}
}
}
