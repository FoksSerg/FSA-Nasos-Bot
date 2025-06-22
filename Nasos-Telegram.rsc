# ===== NASOS TELEGRAM =====
# Модуль обработки команд Telegram бота системы управления насосом
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 19 декабря 2024
# Версия: 1.5

# Объявление глобальных переменных
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

# Импорт переменных для работы с POE интерфейсом
:global MsgPumpOn
:global MsgPumpOff

# Переменные TimeUtils (на случай если понадобятся)
:global InputSeconds
:global FormattedLog
:global FormattedTelegram

# Надежная проверка инициализации системы с повторными попытками
:local initAttempts 0
:local maxInitAttempts 3
:local initSuccess false

:while (!$initSuccess && $initAttempts < $maxInitAttempts) do={
    :set initAttempts ($initAttempts + 1)
    :log warning ("Насос - Попытка инициализации #" . $initAttempts)
    
    # Проверка базовой инициализации
:if ([:typeof $NasosInitStatus] = "nothing" || !$NasosInitStatus) do={
    :log warning "Насос - Запуск Nasos-Init"
    /system script run Nasos-Init
        :delay 2s
}

    # Проверка критичных переменных после инициализации
    :if ([:len $BotToken] = 0 or [:len $ChatId] = 0 or [:len $PoeMainInterface] = 0) do={
        :log error ("Насос - Попытка #" . $initAttempts . ": Критичные переменные не инициализированы")
        :log error ("BotToken length: " . [:len $BotToken])
        :log error ("ChatId length: " . [:len $ChatId]) 
        :log error ("PoeMainInterface length: " . [:len $PoeMainInterface])
        :if ($initAttempts < $maxInitAttempts) do={
            :log warning "Насос - Повторная попытка инициализации через 3 секунды..."
            :delay 3s
        }
    } else={
        :set initSuccess true
        :log info "Насос - Инициализация успешна!"
    }
}

# Критическая ошибка если инициализация не удалась
:if (!$initSuccess) do={
    :log error "Насос - КРИТИЧЕСКАЯ ОШИБКА: Не удалось инициализировать систему после 3 попыток!"
    :error "Initialization failed - check Nasos-Init.rsc and global variables"
}

# Инициализация счетчика циклов и настройка offset для Telegram API
:local loopCounter 0
:if ([:typeof $LastUpdateId] = "nothing" || [:len $LastUpdateId] = 0) do={
    # Получение последнего update_id для пропуска старых сообщений
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

# Функция для создания scheduler'а для изолированного выполнения команд
:global createSafeScheduler do={
    :local schedulerName $1
    :local command $2
    :local delaySeconds $3
    
    # Удаление существующего scheduler'а с таким именем
    :if ([:len [/system scheduler find name=$schedulerName]] > 0) do={
        /system scheduler remove [find name=$schedulerName]
        :log info ("Насос - Удален существующий scheduler: " . $schedulerName)
    }
    
    # Вычисление времени запуска (+delaySeconds)
    :local now [/system clock get time]
    :local hour [:tonum [:pick $now 0 2]]
    :local min [:tonum [:pick $now 3 5]]
    :local sec ([:tonum [:pick $now 6 8]] + $delaySeconds)
    :if ($sec > 59) do={
        :set sec ($sec - 60)
        :set min ($min + 1)
        :if ($min > 59) do={
            :set min ($min - 60)
            :set hour ($hour + 1)
            :if ($hour > 23) do={ :set hour 0 }
        }
    }
    
    # Форматирование времени
    :local hourStr [:tostr $hour]
    :local minStr [:tostr $min] 
    :local secStr [:tostr $sec]
    :if ($hour < 10) do={ :set hourStr ("0" . $hour) }
    :if ($min < 10) do={ :set minStr ("0" . $min) }
    :if ($sec < 10) do={ :set secStr ("0" . $sec) }
    :local startTime ($hourStr . ":" . $minStr . ":" . $secStr)
    
    # Создание scheduler'а
    /system scheduler add name=$schedulerName interval=0 start-time=$startTime on-event=$command
    :log info ("Насос - Создан scheduler: " . $schedulerName . " время: " . $startTime)
}

# Надежная настройка меню Telegram бота с проверками
:local menuAttempts 0
:local maxMenuAttempts 2
:local menuSuccess false

:while (!$menuSuccess && $menuAttempts < $maxMenuAttempts) do={
    :set menuAttempts ($menuAttempts + 1)
    :log info ("Насос - Попытка настройки меню #" . $menuAttempts)
    
    # Попытка запуска модуля настройки меню
    :do {
/system script run Nasos-SetMenu
        :delay 2s
        :set menuSuccess true
:log info "Насос - Меню бота установлено успешно"
    } on-error={
        :log error ("Насос - Ошибка настройки меню, попытка #" . $menuAttempts)
        :if ($menuAttempts < $maxMenuAttempts) do={
            :delay 3s
        }
    }
}

# Если меню не удалось установить - продолжаем без него
:if (!$menuSuccess) do={
    :log warning "Насос - Не удалось установить меню - продолжаем без него"
}

# Запуск основного цикла мониторинга
:log info "Насос - Запуск цикла мониторинга Telegram..."

# Определение текущего статуса насоса для приветственного сообщения
:local poeStatus [/interface ethernet get [find name=$PoeMainInterface] poe-out]
:local currentStatus
:if ($poeStatus = "forced-on") do={
    :set currentStatus $MsgPumpOn
} else={
    :set currentStatus $MsgPumpOff
}

# Отправка приветственного сообщения с меню команд
:local welcomeMsg ($MsgSysStarted . $MsgNewLine . $MsgStatusCurrent . $currentStatus . $MsgNewLine . $MsgNewLine . $MsgMenuHeader . $MsgNewLine . $MsgMenuStop . $MsgNewLine . $MsgMenuStatus . $MsgNewLine . $MsgMenuStart5 . $MsgNewLine . $MsgMenuStart10 . $MsgNewLine . $MsgMenuStart30 . $MsgNewLine . $MsgMenuStart60 . $MsgNewLine . $MsgMenuStart120 . $MsgNewLine . $MsgMenuShow)
/tool fetch url=("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $welcomeMsg) keep-result=no
:log info "Насос - Отправлено приветственное сообщение"

# Основной цикл обработки команд Telegram
:while (true) do={
    :set loopCounter ($loopCounter + 1)
    # Обновление heartbeat для мониторинга работы модуля
    :set TelegramHeartbeat [/system clock get time]
    
    # Получение новых сообщений от Telegram API
    :local getUrl ("https://api.telegram.org/bot" . $BotToken . "/getUpdates?limit=5&offset=" . $LastUpdateId)
    :local updates [/tool fetch url=$getUrl as-value output=user]
    :local content ($updates->"data")
    
    # Обновление offset для следующего запроса
    :local updateIdPos [:find $content "\"update_id\":"]
    :if ([:len $updateIdPos] > 0) do={
        :local idStart ($updateIdPos + 12)
        :local idEnd [:find $content "," $idStart]
        :local newUpdateId [:pick $content $idStart $idEnd]
        :set LastUpdateId ($newUpdateId + 1)
    }
    
    # Обработка команды остановки насоса через изолированный scheduler
    :if ([:len [:find $content "\"text\":\"stop\""]] > 0 or [:len [:find $content "\"text\":\"/stop\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА STOP - создается изолированный scheduler"
        :set NewDuration 0
        [$createSafeScheduler "nasos-cmd-stop" ":global NewDuration; :set NewDuration 0; /system script run Nasos-Runner" 1]
    }
    
    # Обработка команд запуска насоса на разное время через изолированные scheduler'ы
    :if ([:len [:find $content "\"text\":\"start 5\""]] > 0 or [:len [:find $content "\"text\":\"/start5\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА START 5 - создается изолированный scheduler"
        :set NewDuration 300
        [$createSafeScheduler "nasos-cmd-start5" ":global NewDuration; :set NewDuration 300; /system script run Nasos-Runner" 1]
    }
    :if ([:len [:find $content "\"text\":\"start 10\""]] > 0 or [:len [:find $content "\"text\":\"/start10\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА START 10 - создается изолированный scheduler"
        :set NewDuration 600
        [$createSafeScheduler "nasos-cmd-start10" ":global NewDuration; :set NewDuration 600; /system script run Nasos-Runner" 1]
    }
    :if ([:len [:find $content "\"text\":\"start 30\""]] > 0 or [:len [:find $content "\"text\":\"/start30\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА START 30 - создается изолированный scheduler"
        :set NewDuration 1800
        [$createSafeScheduler "nasos-cmd-start30" ":global NewDuration; :set NewDuration 1800; /system script run Nasos-Runner" 1]
    }
    :if ([:len [:find $content "\"text\":\"start 60\""]] > 0 or [:len [:find $content "\"text\":\"/start60\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА START 60 - создается изолированный scheduler"
        :set NewDuration 3600
        [$createSafeScheduler "nasos-cmd-start60" ":global NewDuration; :set NewDuration 3600; /system script run Nasos-Runner" 1]
    }
    :if ([:len [:find $content "\"text\":\"start 120\""]] > 0 or [:len [:find $content "\"text\":\"/start120\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА START 120 - создается изолированный scheduler"
        :set NewDuration 7200
        [$createSafeScheduler "nasos-cmd-start120" ":global NewDuration; :set NewDuration 7200; /system script run Nasos-Runner" 1]
    }
    
    # Обработка команды показа меню
    :if ([:len [:find $content "\"text\":\"menu\""]] > 0 or [:len [:find $content "\"text\":\"/menu\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА MENU - отправляется список команд"
        :local menuText ($MsgMenuHeader . $MsgNewLine . $MsgMenuStop . $MsgNewLine . $MsgMenuStatus . $MsgNewLine . $MsgMenuStart5 . $MsgNewLine . $MsgMenuStart10 . $MsgNewLine . $MsgMenuStart30 . $MsgNewLine . $MsgMenuStart60 . $MsgNewLine . $MsgMenuStart120 . $MsgNewLine . $MsgMenuShow)
        /tool fetch url=("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $menuText) keep-result=no
    }
    
    # Обработка команды проверки статуса
    :if ([:len [:find $content "\"text\":\"status\""]] > 0 or [:len [:find $content "\"text\":\"/status\""]] > 0) do={
        :log warning "Насос - НАЙДЕНА КОМАНДА STATUS - проверяется состояние насоса"
        :local poeStatus [/interface ethernet get [find name=$PoeMainInterface] poe-out]
        :local currentTime [/system clock get time]
        :local statusText ($MsgHeader . $MsgNewLine . $MsgStatusHeader . $MsgNewLine)
        
        # Формирование статуса для работающего насоса
        :if ($poeStatus = "forced-on") do={
            :set statusText ($statusText . $MsgStatusRunning . $MsgNewLine)
            
            # Расчет времени работы
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
            
            # Проверка наличия активного таймера и расчет оставшегося времени
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
            # Формирование статуса для остановленного насоса
            :set statusText ($statusText . $MsgStatusStopped . $MsgNewLine)
            
            # Расчет времени с момента остановки
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
#        /tool fetch url=("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $statusText) keep-result=no
    }
    :delay 4s
} 