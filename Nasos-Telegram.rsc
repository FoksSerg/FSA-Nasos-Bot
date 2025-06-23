# ===== NASOS TELEGRAM v3.1 =====
# Революционный модуль обработки команд Telegram бота
# Построен на архитектуре центрального диспетчера
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 23 июня 2025
# Последнее обновление: 23 июня 2025
# Версия: 3.1 - Интеграция модуля TimeUtils для расчета времени

# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
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
:global LastWorkDuration

# Переменные диспетчера
:global TgAction
:global TgMessage
:global TgKeyboardType

# Переменные сообщений (основные)
:global MsgSysStarted
:global MsgMenuHeader
:global MsgNewLine
:global MsgStatusGetting
:global MsgStatusCurrent
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
:global MsgTimeWorkedHeader
:global MsgTimeMin
:global MsgTimeSec

# Переменные модуля TimeUtils
:global InputSeconds
:global FormattedLog
:global FormattedTelegram

# Переменные статусов насоса
:global MsgPumpOn
:global MsgPumpOff

# Переменные команд меню
:global MsgMenuStop
:global MsgMenuStatus
:global MsgMenuShow
:global MsgMenuStart5
:global MsgMenuStart10
:global MsgMenuStart30
:global MsgMenuStart60
:global MsgMenuStart120

:log info "Насос - Telegram v3.1: Запуск с интеграцией TimeUtils"

# === НАДЕЖНАЯ ИНИЦИАЛИЗАЦИЯ ===
:local initAttempts 0
:local maxInitAttempts 3
:local initSuccess false

:while (!$initSuccess && $initAttempts < $maxInitAttempts) do={
    :set initAttempts ($initAttempts + 1)
    :log warning ("Насос - Инициализация попытка #" . $initAttempts)
    
    # Запуск инициализации если нужно
    :if ([:typeof $NasosInitStatus] = "nothing" || !$NasosInitStatus) do={
        :log warning "Насос - Запуск Nasos-Init"
        /system script run Nasos-Init
        :delay 2s
    }
    
    # Проверка критичных переменных
    :if ([:len $BotToken] = 0 or [:len $ChatId] = 0 or [:len $PoeMainInterface] = 0) do={
        :log error ("Насос - Попытка #" . $initAttempts . ": Критичные переменные не готовы")
        :if ($initAttempts < $maxInitAttempts) do={
            :delay 3s
        }
    } else={
        :set initSuccess true
        :log info "Насос - Инициализация успешна!"
    }
}

# Критическая ошибка инициализации
:if (!$initSuccess) do={
    :log error "Насос - КРИТИЧЕСКАЯ ОШИБКА: Инициализация провалена!"
    :return false
}

# === ИНИЦИАЛИЗАЦИЯ OFFSET ===
:if ([:typeof $LastUpdateId] = "nothing" || [:len $LastUpdateId] = 0) do={
    :log info "Насос - Получение начального offset..."
    :do {
        :local initUpdates [/tool fetch url=("https://api.telegram.org/bot" . $BotToken . "/getUpdates?offset=-1&limit=1") as-value output=user]
        :local initContent ($initUpdates->"data")
        :local updateIdPos [:find $initContent "\"update_id\":"]
        :if ([:len $updateIdPos] > 0) do={
            :local idStart ($updateIdPos + 12)
            :local idEnd [:find $initContent "," $idStart]
            :local latestUpdateId [:pick $initContent $idStart $idEnd]
            :set LastUpdateId ($latestUpdateId + 1)
            :log info ("Насос - Offset установлен: " . $LastUpdateId)
        } else={
            :set LastUpdateId 1
            :log info "Насос - Offset по умолчанию: 1"
        }
    } on-error={
        :set LastUpdateId 1
        :log warning "Насос - Ошибка получения offset, используем: 1"
    }
} else={
    :log info ("Насос - Продолжаем с offset: " . $LastUpdateId)
}

# === ПРИВЕТСТВЕННОЕ СООБЩЕНИЕ ЧЕРЕЗ ДИСПЕТЧЕР ===
:log info "Насос - Отправка приветственного сообщения..."

# Определение текущего статуса насоса
:local poeStatus [/interface ethernet get [find name=$PoeMainInterface] poe-out]
:local statusMsg
:if ($poeStatus = "forced-on") do={
    :set statusMsg $MsgPumpOn
} else={
    :set statusMsg $MsgPumpOff
}

# Формирование приветственного сообщения из готовых компонентов
:local welcomeMsg ($MsgSysStarted . $MsgNewLine . $statusMsg)

:set TgAction "send"
:set TgMessage $welcomeMsg
/system script run Nasos-TG-Activator
:delay 1s

:log info "Насос - Запуск основного цикла мониторинга..."

# === ОСНОВНОЙ ЦИКЛ МОНИТОРИНГА ===
:local loopCounter 0

:while (true) do={
    :set loopCounter ($loopCounter + 1)
    
    # Обновление heartbeat
    :set TelegramHeartbeat [/system clock get time]
    
    # Получение обновлений от Telegram
    :local getUrl ("https://api.telegram.org/bot" . $BotToken . "/getUpdates?limit=5&offset=" . $LastUpdateId)
    :local updates [/tool fetch url=$getUrl as-value output=user]
    :local content ($updates->"data")
    
    # Обработка только если есть контент
    :if ([:len $content] > 10) do={
        
        # Обновление offset
        :local updateIdPos [:find $content "\"update_id\":"]
        :if ([:len $updateIdPos] > 0) do={
            :local idStart ($updateIdPos + 12)
            :local idEnd [:find $content "," $idStart]
            :local newUpdateId [:pick $content $idStart $idEnd]
            :set LastUpdateId ($newUpdateId + 1)
        }
        
        # === ОБРАБОТКА КОМАНД ===
        
        # Команда STOP
        :if ([:len [:find $content "\"/stop\""]] > 0 || [:len [:find $content "\"stop\""]] > 0) do={
            :log warning "Насос - Команда STOP получена"
            :set NewDuration 0
            /system script run Nasos-Runner
        }
        
        # Команда STATUS
        :if ([:len [:find $content "\"/status\""]] > 0 || [:len [:find $content "\"status\""]] > 0) do={
            :log info "Насос - Команда STATUS получена"
            
            # Проверка и исправление неправильного формата LastStopTime
            :if ([:len $LastStopTime] > 8) do={
                :set LastStopTime ""
            }
            
            # Проверка текущего состояния POE порта
            :local poeStatus [/interface ethernet get [find name=$PoeMainInterface] poe-out]
            :local currentTime [/system clock get time]
            :local statusText ($MsgHeader . $MsgNewLine)
            
            :if ($poeStatus = "forced-on") do={
                # Насос работает
                :set statusText ($statusText . $MsgStatusHeader . " " . $MsgStatusRunning . $MsgNewLine)
                
                # Расчет времени работы
                :if ([:len $PoeStartTime] > 0) do={
                    # Ручной расчет разности времени
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
                    
                    # Используем TimeUtils для форматирования
                    :set InputSeconds $workSeconds
                    /system script run Nasos-TimeUtils
                    :set statusText ($statusText . $MsgStatusWorkingTime . $FormattedTelegram . $MsgNewLine)
                }
                
                # Проверка таймера автостопа
                :if ([:len $PoeActiveTimer] > 0 && [:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
                    :local timerInterval [/system scheduler get [find name=$PoeActiveTimer] interval]
                    :local intervalHours [:pick $timerInterval 0 2]
                    :local intervalMins [:pick $timerInterval 3 5]
                    :local intervalSecs [:pick $timerInterval 6 8]
                    :local totalSeconds ($intervalHours * 3600 + $intervalMins * 60 + $intervalSecs)
                    
                    # Расчет оставшегося времени
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
                        :set InputSeconds $remainingSeconds
                        /system script run Nasos-TimeUtils
                        :set statusText ($statusText . $MsgStatusTimeLeft . $FormattedTelegram . $MsgNewLine)
                    } else={
                        :set statusText ($statusText . $MsgStatusTimerExpired . $MsgNewLine)
                    }
                } else={
                    :set statusText ($statusText . $MsgStatusNoAutoStop . $MsgNewLine)
                }
            } else={
                # Насос остановлен
                :set statusText ($statusText . $MsgStatusHeader . " " . $MsgStatusStopped . $MsgNewLine)
                
                # Показ времени последней работы (если есть данные)
                :log info ("Насос - STATUS DEBUG: LastWorkDuration=[" . $LastWorkDuration . "], тип=[" . [:typeof $LastWorkDuration] . "]")
                :if ([:typeof $LastWorkDuration] = "num" && $LastWorkDuration > 0) do={
                    # Используем TimeUtils для форматирования времени работы
                    :set InputSeconds $LastWorkDuration
                    /system script run Nasos-TimeUtils
                    :set statusText ($statusText . $MsgTimeWorkedHeader . " " . $FormattedTelegram . $MsgNewLine)
                    :log info ("Насос - STATUS: Добавлена строка времени работы: " . $FormattedTelegram)
                } else={
                    :log warning ("Насос - STATUS: Время работы НЕ добавлено - нет данных или некорректное значение")
                }
                
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
                    
                    # Используем TimeUtils для форматирования
                    :set InputSeconds $stopDiffSeconds
                    /system script run Nasos-TimeUtils
                    :set statusText ($statusText . $MsgStatusStoppedTime . $FormattedTelegram . $MsgStatusTimeAgo . $MsgNewLine)
                } else={
                    :set statusText ($statusText . $MsgStatusLastStopUnknown . $MsgNewLine)
                }
            }
            
            # Отправка статуса через диспетчер
            :set TgAction "send"
            :set TgMessage $statusText
            /system script run Nasos-TG-Activator
        }
        
                 # Команда MENU
         :if ([:len [:find $content "\"/menu\""]] > 0 || [:len [:find $content "\"menu\""]] > 0) do={
             :log info "Насос - Команда MENU получена"
             :local menuMsg ($MsgMenuHeader . $MsgNewLine . $MsgNewLine . $MsgMenuStop . $MsgNewLine . $MsgMenuStatus . $MsgNewLine . $MsgMenuShow . $MsgNewLine . $MsgNewLine . $MsgMenuStart5 . $MsgNewLine . $MsgMenuStart10 . $MsgNewLine . $MsgMenuStart30 . $MsgNewLine . $MsgMenuStart60 . $MsgNewLine . $MsgMenuStart120)
             
             :set TgAction "send"
             :set TgMessage $menuMsg
             /system script run Nasos-TG-Activator
         }
        
        # Команды запуска START5
        :if ([:len [:find $content "\"/start5\""]] > 0 || [:len [:find $content "\"start 5\""]] > 0) do={
            :log warning "Насос - Команда START5 получена"
            :set NewDuration 300
            /system script run Nasos-Runner
        }
        
        # Команды запуска START10
        :if ([:len [:find $content "\"/start10\""]] > 0 || [:len [:find $content "\"start 10\""]] > 0) do={
            :log warning "Насос - Команда START10 получена"
            :set NewDuration 600
            /system script run Nasos-Runner
        }
        
        # Команды запуска START30
        :if ([:len [:find $content "\"/start30\""]] > 0 || [:len [:find $content "\"start 30\""]] > 0) do={
            :log warning "Насос - Команда START30 получена"
            :set NewDuration 1800
            /system script run Nasos-Runner
        }
        
        # Команды запуска START60
        :if ([:len [:find $content "\"/start60\""]] > 0 || [:len [:find $content "\"start 60\""]] > 0) do={
            :log warning "Насос - Команда START60 получена"
            :set NewDuration 3600
            /system script run Nasos-Runner
        }
        
        # Команды запуска START120
        :if ([:len [:find $content "\"/start120\""]] > 0 || [:len [:find $content "\"start 120\""]] > 0) do={
            :log warning "Насос - Команда START120 получена"
            :set NewDuration 7200
            /system script run Nasos-Runner
        }
        
        # Логирование каждого 50-го цикла для мониторинга
        :if (($loopCounter % 50) = 0) do={
            :log info ("Насос - Цикл #" . $loopCounter . ", heartbeat: " . $TelegramHeartbeat)
        }
    }
    
    # Пауза между циклами
    :delay 4s
}