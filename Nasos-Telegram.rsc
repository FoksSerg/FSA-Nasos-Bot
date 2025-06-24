# ===== NASOS TELEGRAM v4.0 =====
# Революционный модуль обработки команд Telegram бота
# Построен на архитектуре центрального диспетчера
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 23 июня 2025
# Последнее обновление: 23 июня 2025
# Версия: 4.1 - Исправлено форматирование STATUS, добавлена защита от висящих таймеров

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
:global MsgSysError
:global MsgEmergencyShutdown
:global MsgEmergencyReason
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

# Переменные нового опроса API
:global TgLastCommand
:global TgCommandTime
:global TgPollStatus
:global TgPollError
:global TgPollHeartbeat
:global TgStartMinutes

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
    # Защита от пустых значений
    :if ([:typeof $timeStr] = "nothing" || [:len $timeStr] = 0 || [:len $timeStr] < 8) do={
        :return 0
    }
    :local hours [:pick $timeStr 0 2]
    :local minutes [:pick $timeStr 3 5]
    :local seconds [:pick $timeStr 6 8]
    # Защита от нечисловых значений
    :if ([:typeof [:tonum $hours]] = "nothing" || [:typeof [:tonum $minutes]] = "nothing" || [:typeof [:tonum $seconds]] = "nothing") do={
        :return 0
    }
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
:do {
    /system script run Nasos-TG-Activator
} on-error={
    :log warning "Насос - Ошибка отправки приветствия"
}
:delay 1s

# === ОТКАЗОУСТОЙЧИВЫЙ ЦИКЛ МОНИТОРИНГА ===
:local loopCounter 0
:while (true) do={
    :set loopCounter ($loopCounter + 1)
    
    # Обновление heartbeat
    :set TelegramHeartbeat [/system clock get time]
    
    # КРИТИЧЕСКАЯ ПРОВЕРКА: Насос не должен работать без автостопа!
    :local poeStatus [/interface ethernet poe get $PoeMainInterface poe-out]
    :if ($poeStatus = "auto-on" || $poeStatus = "forced-on") do={
        :if ([:len $PoeActiveTimer] = 0 || [:len [/system scheduler find name=$PoeActiveTimer]] = 0) do={
            :log error "КРИТИЧНО: Насос работает без автостопа - принудительное отключение!"
            
            # Немедленное отключение насоса
            /interface ethernet poe set $PoeMainInterface poe-out=off
            
            # Расчет времени работы для отчета
            :local emergencyWorkSeconds 0
            :if ([:len $PoeStartTime] > 0) do={
                :local currentTime [/system clock get time]
                :local startSeconds [$timeToSeconds $PoeStartTime]
                :local currentSeconds [$timeToSeconds $currentTime]
                
                :if ($startSeconds >= 0 && $currentSeconds >= 0) do={
                    :set emergencyWorkSeconds ($currentSeconds - $startSeconds)
                    :if ($emergencyWorkSeconds < 0) do={
                        :set emergencyWorkSeconds ($emergencyWorkSeconds + 86400)
                    }
                }
            }
            
            # Сохранение данных об аварийной остановке
            :set LastStopTime [/system clock get time]
            :set LastWorkDuration $emergencyWorkSeconds
                            :set PoeStartTime ""
                :set ExpectedStopTime ""
            :set PoeActiveTimer ""
            
            # Принудительное удаление таймера по фиксированному имени
            :if ([:len [/system scheduler find name=$PoeTimerName]] > 0) do={
                /system scheduler remove [find name=$PoeTimerName]
                :log warning ("Насос - Принудительно удален таймер при аварийном отключении: " . $PoeTimerName)
            }
            
            # Отправка критического уведомления
            :local emergencyMsg ($MsgSysError . $MsgEmergencyShutdown . $MsgNewLine . $MsgEmergencyReason)
            :if ($emergencyWorkSeconds > 0) do={
                :set InputSeconds $emergencyWorkSeconds
                :do {
                    /system script run Nasos-TimeUtils
                    :set emergencyMsg ($emergencyMsg . $MsgNewLine . $MsgTimeWorkedHeader . " " . $FormattedTelegram)
                } on-error={}
            }
            
            # Немедленная отправка уведомления
            :set TgAction "send"
            :set TgMessage $emergencyMsg
            :do {
                /system script run Nasos-TG-Activator
            } on-error={}
        }
    }
    
    # Безопасный опрос API через TG-Activator
    :set TgAction "poll"
    :do {
        /system script run Nasos-TG-Activator
    } on-error={
        :log warning "Насос - Ошибка запуска TG-Activator"
        :set TgPollStatus "error"
        :set TgPollError "Ошибка запуска активатора"
    }
    :delay 1s
    
    # Проверка наличия команды для обработки
    :if ([:len $TgLastCommand] > 0 && $TgPollStatus = "ok") do={
        
        # === ОБРАБОТКА КОМАНД ===
       
        # Универсальная команда START с поддержкой положительных, отрицательных и нулевых значений
        :if ($TgLastCommand = "start") do={
            :local minutes $TgStartMinutes
            # Защита от пустых или некорректных значений
            :if ([:typeof $minutes] = "nothing" || [:typeof $minutes] != "num") do={
                :log warning "Ошибка: некорректное значение минут"
                :set TgLastCommand ""
            } else={
                :if ($minutes = 0) do={
                    :log warning "СТОП (через start0)"
                    :set NewDuration 0
                } else={
                    :if ($minutes > 0) do={
                        :log warning ("СТАРТ " . $minutes . " мин")
                    } else={
                        :log warning ("УМЕНЬШЕНИЕ на " . ($minutes * -1) . " мин")
                    }
                    :set NewDuration ($minutes * 60)
                }
                :do {
                    /system script run Nasos-Runner
                } on-error={
                    :log warning "Ошибка запуска Runner"
                }
                :set TgLastCommand ""
            }
        }
       
        # Команда STOP
        :if ($TgLastCommand = "stop") do={
            :log warning "СТОП"
            :set NewDuration 0
            /system script run Nasos-Runner
            :set TgLastCommand ""
        }
        
        # Команда STATUS
        :if ($TgLastCommand = "status") do={
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
                :set statusText ($statusText . $MsgStatusHeader . " " . $MsgPumpOn)
                
                # Расчет времени работы
                :local workSeconds 0
                :if ([:len $PoeStartTime] > 0) do={
                    # Расчет разности времени через функцию с защитой
                    :local startSeconds [$timeToSeconds $PoeStartTime]
                    :local currentSeconds [$timeToSeconds $currentTime]
                    
                    # Защита от некорректных значений времени
                    :if ($startSeconds >= 0 && $currentSeconds >= 0) do={
                    :set workSeconds ($currentSeconds - $startSeconds)
                    :if ($workSeconds < 0) do={
                        :set workSeconds ($workSeconds + 86400)
                    }
                        
                        # Используем TimeUtils для форматирования с защитой
                        :if ($workSeconds >= 0) do={
                            :set InputSeconds $workSeconds
                            :do {
                                /system script run Nasos-TimeUtils
                                :set statusText ($statusText . $MsgNewLine . $MsgStatusWorkingTime . $FormattedTelegram)
                            } on-error={
                                :set statusText ($statusText . $MsgNewLine . $MsgStatusWorkingTime . "ошибка расчета")
                            }
                        }
                    }
                }
                
                # Проверка таймера автостопа
                :if ([:len $PoeActiveTimer] > 0 && [:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
                    :local timerInterval [/system scheduler get [find name=$PoeActiveTimer] interval]
                    :local totalSeconds [$timeToSeconds $timerInterval]
                    
                    # Расчет оставшегося времени через ExpectedStopTime с защитой
                    :local remainingSeconds 0
                    :if ([:len $ExpectedStopTime] > 0) do={
                        :local currentTime [/system clock get time]
                        :local currentSeconds [$timeToSeconds $currentTime]
                        :local stopSeconds [$timeToSeconds $ExpectedStopTime]
                        
                        # Защита от некорректных значений
                        :if ($currentSeconds >= 0 && $stopSeconds >= 0) do={
                            :set remainingSeconds ($stopSeconds - $currentSeconds)
                            :if ($remainingSeconds < 0) do={
                                :set remainingSeconds ($remainingSeconds + 86400)
                            }
                            :if ($remainingSeconds > 86400) do={
                                :set remainingSeconds 0
                            }
                        }
                    }

                :if ($remainingSeconds > 0) do={
                        :set InputSeconds $remainingSeconds
                        :do {
                            /system script run Nasos-TimeUtils
                            :set statusText ($statusText . $MsgNewLine . $MsgStatusTimeLeft . $FormattedTelegram)
                        } on-error={
                            :set statusText ($statusText . $MsgNewLine . $MsgStatusTimeLeft . "ошибка расчета")
                        }
                        
                        # Ожидаемое общее время = текущее время работы + оставшееся время
                        :local expectedTotalSeconds ($workSeconds + $remainingSeconds)
                        :if ($expectedTotalSeconds >= 0) do={
                            :set InputSeconds $expectedTotalSeconds
                            :do {
                                /system script run Nasos-TimeUtils
                                :set statusText ($statusText . $MsgNewLine . $MsgTimeExpectedTotal . " " . $FormattedTelegram)
                            } on-error={
                                :set statusText ($statusText . $MsgNewLine . $MsgTimeExpectedTotal . " ошибка расчета")
                            }
                        }
                    } else={
                        :set statusText ($statusText . $MsgNewLine . $MsgStatusTimerExpired)
                    }
                } else={
                    :set statusText ($statusText . $MsgNewLine . $MsgStatusNoAutoStop)
                }
            } else={
                # Насос остановлен
                :set statusText ($statusText . $MsgStatusHeader . " " . $MsgPumpOff)
            
                # Расчет времени с момента остановки (показываем первым)
            :if ([:len $LastStopTime] > 0) do={
                    :local stopSeconds [$timeToSeconds $LastStopTime]
                    :local currentSeconds [$timeToSeconds $currentTime]
                    
                    # Защита от некорректных значений
                    :if ($stopSeconds >= 0 && $currentSeconds >= 0) do={
                :local stopDiffSeconds ($currentSeconds - $stopSeconds)
                :if ($stopDiffSeconds < 0) do={
                    :set stopDiffSeconds ($stopDiffSeconds + 86400)
                }
                        
                        # Используем TimeUtils для форматирования с защитой
                        :if ($stopDiffSeconds >= 0) do={
                            :set InputSeconds $stopDiffSeconds
                            :do {
                                /system script run Nasos-TimeUtils
                                :set statusText ($statusText . $MsgNewLine . $MsgStatusStoppedTime . $FormattedTelegram . $MsgStatusTimeAgo)
                            } on-error={
                                :set statusText ($statusText . $MsgNewLine . $MsgStatusStoppedTime . "ошибка расчета" . $MsgStatusTimeAgo)
                            }
                        }
                    } else={
                        :set statusText ($statusText . $MsgNewLine . $MsgStatusLastStopUnknown)
                    }
            } else={
                    :set statusText ($statusText . $MsgNewLine . $MsgStatusLastStopUnknown)
                }
                
                # Показ времени последней работы (показываем вторым)
                :if ([:typeof $LastWorkDuration] = "num" && $LastWorkDuration > 0) do={
                    # Используем TimeUtils для форматирования времени работы с защитой
                    :set InputSeconds $LastWorkDuration
                    :do {
                        /system script run Nasos-TimeUtils
                        :set statusText ($statusText . $MsgNewLine . $MsgTimeWorkedHeader . " " . $FormattedTelegram)
                    } on-error={
                        :set statusText ($statusText . $MsgNewLine . $MsgTimeWorkedHeader . " ошибка расчета")
                    }
                }
            }
            # Отправка статуса через диспетчер
            :set TgAction "send"
            :set TgMessage $statusText
            :do {
                /system script run Nasos-TG-Activator
            } on-error={
                :log warning "Насос - Ошибка отправки STATUS"
            }
            :set TgLastCommand ""
        }
        
        # Команда MENU
        :if ($TgLastCommand = "menu") do={
            :local menuMsg ($MsgMenuHeader . $MsgNewLine . $MsgNewLine . $MsgMenuStop . $MsgNewLine . $MsgMenuStatus . $MsgNewLine . $MsgMenuShow . $MsgNewLine . $MsgNewLine . $MsgMenuStart5 . $MsgNewLine . $MsgMenuStart10 . $MsgNewLine . $MsgMenuStart30 . $MsgNewLine . $MsgMenuStart60 . $MsgNewLine . $MsgMenuStart120)
            :set TgAction "send"
            :set TgMessage $menuMsg
            :do {
                /system script run Nasos-TG-Activator
            } on-error={
                :log warning "Насос - Ошибка отправки MENU"
            }
            :set TgLastCommand ""
        }
        

        
    } else={
        # Обработка ошибок API или отсутствия команд
        :if ($TgPollStatus = "error") do={
            :log warning ("Насос - Ошибка API: " . $TgPollError)
        }
    }
    # Пауза между циклами
    :delay 4s
} 