:global NasosInitStatus
:global BotToken
:global ChatId
:global LastUpdateId
:global TelegramHeartbeat
:global NewDuration
:global PoeMainInterface
:global PoeStartTime
:global PoeActiveTimer
:global LastStopTime

# Импорт переменных сообщений
:global MsgSysStarted
:global MsgStatusCurrent
:global MsgMenuHeader
:global MsgMenuStop
:global MsgMenuStatus
:global MsgMenuStart5
:global MsgMenuStart10
:global MsgMenuStart30
:global MsgMenuStart60
:global MsgMenuStart120
:global MsgMenuShow
:global MsgHeader
:global MsgStatusHeader
:global MsgStatusRunning
:global MsgStatusStopped
:global MsgStatusWorkingTime
:global MsgStatusTimeLeft
:global MsgStatusTimerExpired
:global MsgStatusNoAutoStop
:global MsgStatusStoppedTime
:global MsgStatusTimeAgo
:global MsgStatusLastStopUnknown
:global MsgTimeMin
:global MsgTimeSec
:global MsgNewLine

:if ([:typeof $NasosInitStatus] = "nothing" || !$NasosInitStatus) do={
    :log warning "Насос - Запуск Nasos-Init"
    /system script run Nasos-Init
}
:if ([:len $BotToken] = 0 or [:len $ChatId] = 0) do={
    :log error "Насос - КРИТИЧЕСКАЯ ОШИБКА: BotToken или ChatId не определены!"
}
:local loopCounter 0
:if ([:typeof $LastUpdateId] = "nothing" || [:len $LastUpdateId] = 0) do={
    :local initUpdates [/tool fetch url=("https://api.telegram.org/bot" . $BotToken . "/getUpdates?offset=-1&limit=1") as-value output=user]
    :local initContent ($initUpdates->"data")
    :local updateIdPos [:find $initContent "\"update_id\":"]
    :if ([:len $updateIdPos] > 0) do={
        :local idStart ($updateIdPos + 12)
        :local idEnd [:find $initContent "," $idStart]
        :local latestUpdateId [:pick $initContent $idStart $idEnd]
        :set LastUpdateId ($latestUpdateId + 1)
        :log warning ("Насос - Telegram запущен, пропускаем старые сообщения с offset: " . $LastUpdateId)
    } else={
        :set LastUpdateId 1
        :log warning "Насос - Telegram запущен, старых сообщений не найдено"
    }
} else={
    :log info ("Насос - Telegram продолжает работу с LastUpdateId: " . $LastUpdateId)
}
:log info "Насос - Настройка меню Telegram бота..."
:log warning "Насос - Запуск Nasos-SetMenu"
/system script run Nasos-SetMenu
:log info "Насос - Меню бота установлено успешно"
:log info "Насос - Запуск цикла мониторинга Telegram..."
:local poeStatus [/interface ethernet get [find name=$PoeMainInterface] poe-out]
:local currentStatus
:if ($poeStatus = "forced-on") do={
    :set currentStatus $MsgPumpOn
} else={
    :set currentStatus $MsgPumpOff
}
:local welcomeMsg ($MsgSysStarted . $MsgNewLine . $MsgStatusCurrent . $currentStatus . $MsgNewLine . $MsgNewLine . $MsgMenuHeader . $MsgNewLine . $MsgMenuStop . $MsgNewLine . $MsgMenuStatus . $MsgNewLine . $MsgMenuStart5 . $MsgNewLine . $MsgMenuStart10 . $MsgNewLine . $MsgMenuStart30 . $MsgNewLine . $MsgMenuStart60 . $MsgNewLine . $MsgMenuStart120 . $MsgNewLine . $MsgMenuShow)
/tool fetch url=("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $welcomeMsg) keep-result=no
:log info "Насос - Отправлено приветственное сообщение"
:while (true) do={
    :set loopCounter ($loopCounter + 1)
    :set TelegramHeartbeat [/system clock get time]
    :local getUrl ("https://api.telegram.org/bot" . $BotToken . "/getUpdates?limit=5&offset=" . $LastUpdateId)
    :local updates [/tool fetch url=$getUrl as-value output=user]
    :local content ($updates->"data")
    :local updateIdPos [:find $content "\"update_id\":"]
    :if ([:len $updateIdPos] > 0) do={
        :local idStart ($updateIdPos + 12)
        :local idEnd [:find $content "," $idStart]
        :local newUpdateId [:pick $content $idStart $idEnd]
        :set LastUpdateId ($newUpdateId + 1)
    }
    :if ([:len [:find $content "\"text\":\"stop\""]] > 0 or [:len [:find $content "\"text\":\"/stop\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА STOP - выполняется Nasos-Runner"
        :set NewDuration 0
        /system script run Nasos-Runner
    }
    :if ([:len [:find $content "\"text\":\"start 5\""]] > 0 or [:len [:find $content "\"text\":\"/start5\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА START 5 - выполняется Nasos-Runner"
        :set NewDuration 300
        /system script run Nasos-Runner
    }
    :if ([:len [:find $content "\"text\":\"start 10\""]] > 0 or [:len [:find $content "\"text\":\"/start10\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА START 10 - выполняется Nasos-Runner"
        :set NewDuration 600
        /system script run Nasos-Runner
    }
    :if ([:len [:find $content "\"text\":\"start 30\""]] > 0 or [:len [:find $content "\"text\":\"/start30\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА START 30 - выполняется Nasos-Runner"
        :set NewDuration 1800
        /system script run Nasos-Runner
    }
    :if ([:len [:find $content "\"text\":\"start 60\""]] > 0 or [:len [:find $content "\"text\":\"/start60\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА START 60 - выполняется Nasos-Runner"
        :set NewDuration 3600
        /system script run Nasos-Runner
    }
    :if ([:len [:find $content "\"text\":\"start 120\""]] > 0 or [:len [:find $content "\"text\":\"/start120\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА START 120 - выполняется Nasos-Runner"
        :set NewDuration 7200
        /system script run Nasos-Runner
    }
    :if ([:len [:find $content "\"text\":\"menu\""]] > 0 or [:len [:find $content "\"text\":\"/menu\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА MENU - отправляется список команд"
        :local menuText ($MsgMenuHeader . $MsgNewLine . $MsgMenuStop . $MsgNewLine . $MsgMenuStatus . $MsgNewLine . $MsgMenuStart5 . $MsgNewLine . $MsgMenuStart10 . $MsgNewLine . $MsgMenuStart30 . $MsgNewLine . $MsgMenuStart60 . $MsgNewLine . $MsgMenuStart120 . $MsgNewLine . $MsgMenuShow)
        /tool fetch url=("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $menuText) keep-result=no
    }
    :if ([:len [:find $content "\"text\":\"status\""]] > 0 or [:len [:find $content "\"text\":\"/status\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА STATUS - проверяется состояние насоса"
        :local poeStatus [/interface ethernet get [find name=$PoeMainInterface] poe-out]
        :local currentTime [/system clock get time]
        :local statusText ($MsgHeader . $MsgNewLine . $MsgStatusHeader . $MsgNewLine)
        :if ($poeStatus = "forced-on") do={
            :set statusText ($statusText . $MsgStatusRunning . $MsgNewLine)
            :if ([:len $PoeStartTime] > 0) do={
                :local startHours [:pick $PoeStartTime 0 2]
                :local startMinutes [:pick $PoeStartTime 3 5]
                :local startSecs [:pick $PoeStartTime 6 8]
                :local startSeconds ($startHours * 3600 + $startMinutes * 60 + $startSecs)
                :local currentHours [:pick $currentTime 0 2]
                :local currentMins [:pick $currentTime 3 5]
                :local currentSecs [:pick $currentTime 6 8]
                :local currentSeconds ($currentHours * 3600 + $currentMins * 60 + $currentSecs)
                :local workSeconds ($currentSeconds - $startSeconds)
                :if ($workSeconds < 0) do={
                    :set workSeconds ($workSeconds + 86400)
                }
                :local workMinutes ($workSeconds / 60)
                :local workSecondsRem ($workSeconds - ($workMinutes * 60))
                :set statusText ($statusText . $MsgStatusWorkingTime . [:tostr $workMinutes] . $MsgTimeMin . [:tostr $workSecondsRem] . $MsgTimeSec . $MsgNewLine)
            }
            :if ([:len $PoeActiveTimer] > 0 && [:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
                :local timerInterval [/system scheduler get [find name=$PoeActiveTimer] interval]
                :local intervalHours [:pick $timerInterval 0 2]
                :local intervalMins [:pick $timerInterval 3 5]
                :local intervalSecs [:pick $timerInterval 6 8]
                :local totalSeconds ($intervalHours * 3600 + $intervalMins * 60 + $intervalSecs)
                :local workSeconds 0
                :if ([:len $PoeStartTime] > 0) do={
                    :local startHours [:pick $PoeStartTime 0 2]
                    :local startMinutes [:pick $PoeStartTime 3 5]
                    :local startSecs [:pick $PoeStartTime 6 8]
                    :local startSeconds ($startHours * 3600 + $startMinutes * 60 + $startSecs)
                    :local currentHours [:pick $currentTime 0 2]
                    :local currentMins [:pick $currentTime 3 5]
                    :local currentSecs [:pick $currentTime 6 8]
                    :local currentSeconds ($currentHours * 3600 + $currentMins * 60 + $currentSecs)
                    :set workSeconds ($currentSeconds - $startSeconds)
                    :if ($workSeconds < 0) do={
                        :set workSeconds ($workSeconds + 86400)
                    }
                }
                :local remainingSeconds ($totalSeconds - $workSeconds)
                :if ($remainingSeconds > 0) do={
                    :local remainingMinutes ($remainingSeconds / 60)
                    :local remainingSecondsRem ($remainingSeconds - ($remainingMinutes * 60))
                    :set statusText ($statusText . $MsgStatusTimeLeft . [:tostr $remainingMinutes] . $MsgTimeMin . [:tostr $remainingSecondsRem] . $MsgTimeSec . $MsgNewLine)
                } else={
                    :set statusText ($statusText . $MsgStatusTimerExpired . $MsgNewLine)
                }
            } else={
                :set statusText ($statusText . $MsgStatusNoAutoStop . $MsgNewLine)
            }
        } else={
            :set statusText ($statusText . $MsgStatusStopped . $MsgNewLine)
            :if ([:len $LastStopTime] > 0) do={
                :local stopHours [:pick $LastStopTime 0 2]
                :local stopMinutes [:pick $LastStopTime 3 5]
                :local stopSecs [:pick $LastStopTime 6 8]
                :local stopSeconds ($stopHours * 3600 + $stopMinutes * 60 + $stopSecs)
                :local currentHours [:pick $currentTime 0 2]
                :local currentMins [:pick $currentTime 3 5]
                :local currentSecs [:pick $currentTime 6 8]
                :local currentSeconds ($currentHours * 3600 + $currentMins * 60 + $currentSecs)
                :local stopDiffSeconds ($currentSeconds - $stopSeconds)
                :if ($stopDiffSeconds < 0) do={
                    :set stopDiffSeconds ($stopDiffSeconds + 86400)
                }
                :local stopDiffMinutes ($stopDiffSeconds / 60)
                :local stopDiffSecondsRem ($stopDiffSeconds - ($stopDiffMinutes * 60))
                :set statusText ($statusText . $MsgStatusStoppedTime . [:tostr $stopDiffMinutes] . $MsgTimeMin . [:tostr $stopDiffSecondsRem] . $MsgTimeSec . $MsgStatusTimeAgo . $MsgNewLine)
            } else={
                :set statusText ($statusText . $MsgStatusLastStopUnknown . $MsgNewLine)
            }
        }
        /tool fetch url=("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $statusText) keep-result=no
    }
    :delay 4s
} 