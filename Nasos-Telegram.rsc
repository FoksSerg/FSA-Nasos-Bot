# ===== NASOS TELEGRAM v4.0 =====
# Революционный модуль обработки команд Telegram бота
# Построен на архитектуре центрального диспетчера
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 23 июня 2025
# Последнее обновление: 23 июня 2025
# Версия: 4.0 - Оптимизированная версия (-35 строк, +функция timeToSeconds)

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

# Переменные сообщений (основные)
:global MsgSysStarted
:global MsgMenuHeader
:global MsgNewLine
:global MsgHeader
:global MsgStatusHeader
:global MsgPumpOn
:global MsgPumpOff
:global MsgStatusWorkingTime
:global MsgStatusTimeLeft
:global MsgStatusTimerExpired
:global MsgStatusNoAutoStop
:global MsgStatusStoppedTime
:global MsgStatusTimeAgo
:global MsgTimeExpectedTotal
:global MsgStatusLastStopUnknown
:global ExpectedStopTime
:global MsgTimeWorkedHeader

# Переменные модуля TimeUtils
:global InputSeconds
:global FormattedTelegram

# Переменные команд меню
:global MsgMenuStop
:global MsgMenuStatus
:global MsgMenuShow
:global MsgMenuStart5
:global MsgMenuStart10
:global MsgMenuStart30
:global MsgMenuStart60
:global MsgMenuStart120

# === ФУНКЦИЯ РАСЧЕТА ВРЕМЕНИ ===
:global timeToSeconds do={
    :local timeStr $1
    :local hours [:pick $timeStr 0 2]
    :local minutes [:pick $timeStr 3 5]
    :local seconds [:pick $timeStr 6 8]
    :return ($hours * 3600 + $minutes * 60 + $seconds)
}

:log info "Насос - Telegram v4.0: Запуск оптимизированной версии"

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
                :set statusText ($statusText . $MsgStatusHeader . " " . $MsgPumpOn . $MsgNewLine)
                
                # Расчет времени работы
                :local workSeconds 0
                :if ([:len $PoeStartTime] > 0) do={
                    # Расчет разности времени через функцию
                    :local startSeconds [$timeToSeconds $PoeStartTime]
                    :local currentSeconds [$timeToSeconds $currentTime]
                    
                    :set workSeconds ($currentSeconds - $startSeconds)
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
                    :local totalSeconds [$timeToSeconds $timerInterval]
                    
                    # Расчет оставшегося времени через ExpectedStopTime
                    :local remainingSeconds 0
                    :if ([:len $ExpectedStopTime] > 0) do={
                        :local currentTime [/system clock get time]
                        :local currentSeconds [$timeToSeconds $currentTime]
                        :local stopSeconds [$timeToSeconds $ExpectedStopTime]
                        
                        :set remainingSeconds ($stopSeconds - $currentSeconds)
                        :if ($remainingSeconds < 0) do={
                            :set remainingSeconds ($remainingSeconds + 86400)
                        }
                        :if ($remainingSeconds > 86400) do={
                            :set remainingSeconds 0
                        }
                    }

                    
                    :if ($remainingSeconds > 0) do={
                        :set InputSeconds $remainingSeconds
                        /system script run Nasos-TimeUtils
                        :set statusText ($statusText . $MsgStatusTimeLeft . $FormattedTelegram . $MsgNewLine)
                        
                        # Ожидаемое общее время = текущее время работы + оставшееся время
                        :local expectedTotalSeconds ($workSeconds + $remainingSeconds)
                        :set InputSeconds $expectedTotalSeconds
                        /system script run Nasos-TimeUtils
                        :set statusText ($statusText . $MsgTimeExpectedTotal . " " . $FormattedTelegram . $MsgNewLine)
                    } else={
                        :set statusText ($statusText . $MsgStatusTimerExpired . $MsgNewLine)
                    }
                } else={
                    :set statusText ($statusText . $MsgStatusNoAutoStop . $MsgNewLine)
                }
            } else={
                # Насос остановлен
                :set statusText ($statusText . $MsgStatusHeader . " " . $MsgPumpOff)
                
                # Расчет времени с момента остановки (показываем первым)
                :if ([:len $LastStopTime] > 0) do={
                    :local stopSeconds [$timeToSeconds $LastStopTime]
                    :local currentSeconds [$timeToSeconds $currentTime]
                    
                    :local stopDiffSeconds ($currentSeconds - $stopSeconds)
                    :if ($stopDiffSeconds < 0) do={
                        :set stopDiffSeconds ($stopDiffSeconds + 86400)
                    }
                    
                    # Используем TimeUtils для форматирования
                    :set InputSeconds $stopDiffSeconds
                    /system script run Nasos-TimeUtils
                    :set statusText ($statusText . $MsgNewLine . $MsgStatusStoppedTime . $FormattedTelegram . $MsgStatusTimeAgo)
                } else={
                    :set statusText ($statusText . $MsgNewLine . $MsgStatusLastStopUnknown)
                }
                
                # Показ времени последней работы (показываем вторым)
                :if ([:typeof $LastWorkDuration] = "num" && $LastWorkDuration > 0) do={
                    # Используем TimeUtils для форматирования времени работы
                    :set InputSeconds $LastWorkDuration
                    /system script run Nasos-TimeUtils
                    :set statusText ($statusText . $MsgNewLine . $MsgTimeWorkedHeader . " " . $FormattedTelegram . $MsgNewLine)
                    :log info ("Насос - STATUS: Добавлена строка времени работы: " . $FormattedTelegram)
                } else={
                    :log warning ("Насос - STATUS: Время работы НЕ добавлено - нет данных или некорректное значение")
                    :set statusText ($statusText . $MsgNewLine)
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