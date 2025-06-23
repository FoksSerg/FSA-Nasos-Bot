# ===== NASOS RUNNER =====
# Основной модуль управления POE насосом через Telegram бота
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 19 декабря 2024
# Версия: 1.5
# Объявление глобальных переменных
:global NasosInitStatus
:global BotToken
:global ChatId
:global PoeMainInterface
:global NewDuration
:global PoeActiveTimer
:global PoeStartTime
:global PoeTimerName
:global LastStopTime
:global LastWorkDuration
:global MsgSysStarted
:global MsgSysError
:global MsgSysWarning
:global MsgPumpOn
:global MsgPumpOff
:global MsgPumpAlreadyOn
:global MsgPumpStopped
:global MsgPumpAutoStop
:global MsgPumpManualStop
:global MsgPumpStoppedByCmd
:global MsgPumpStoppedTimeReduced
:global MsgTimeWorked
:global MsgTimeWillWork
:global MsgTimeTotal
:global MsgTimeMin
:global MsgTimeSec
:global MsgTimeReduced
:global MsgMenuHeader
:global MsgMenuStop
:global MsgMenuStatus
:global MsgMenuStart5
:global MsgMenuStart10
:global MsgMenuStart30
:global MsgMenuStart60
:global MsgMenuStart120
:global MsgMenuShow
:global MsgStatusRunning
:global MsgStatusStopped
:global MsgStatusCurrent
:global MsgSysReboot
:global MsgTimeWorkedTemplate
:global MsgTimeAlreadyWorkedTemplate
:global MsgTimeAlreadyWorkedTranslit
:global MsgNewLine
:global MsgHeader
:global MsgStatusHeader
:global MsgTimeRemaining
:global MsgTimeExtension
:global MsgTimeExpectedTotal
:global MsgTimeWorkedHeader
:global MsgPumpStartedFor
:global MsgStopCmdTemplate
:global MsgPumpAlreadyStopped
:global MsgTimeSinceStop
# Переменные TimeUtils
:global InputSeconds
:global FormattedLog
:global FormattedTelegram
# Проверка инициализации системы
:if ([:typeof $NasosInitStatus] = "nothing" || !$NasosInitStatus) do={
    :log warning "Насос - Запуск Nasos-Init"
    /system script run Nasos-Init
}
# Проверка обязательных глобальных переменных
:if ([:len $BotToken] = 0 or [:len $ChatId] = 0 or [:len $PoeMainInterface] = 0) do={
    :log error "Насос - КРИТИЧЕСКАЯ ОШИБКА: Обязательные глобальные переменные не определены!"
}
# Функция отправки сообщений в Telegram
:local sendTelegram do={
    :local token $1
    :local chatId $2
    :local message $3
    :local url "https://api.telegram.org/bot$token/sendMessage"
    /tool fetch url=$url http-method=post http-data="chat_id=$chatId&text=$message" keep-result=no
}
# Проверка существования POE интерфейса
:if ([:len [/interface ethernet find name=$PoeMainInterface]] = 0) do={
    :log error "Насос - POE интерфейс не найден"
    $sendTelegram $BotToken $ChatId ($MsgSysStarted . $MsgNewLine . $MsgSysError . "POE%20%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D1%84%D0%B5%D0%B9%D1%81%20%D0%BD%D0%B5%20%D0%BD%D0%B0%D0%B9%D0%B4%D0%B5%D0%BD")
} else={
    # Отладочная информация о текущем статусе POE
    :local currentPoeStatus [/interface ethernet get [find name=$PoeMainInterface] poe-out]
    :log warning ("Насос - ОТЛАДКА: Текущий статус POE при запуске = [" . $currentPoeStatus . "]")
    # Проверка наличия команды на выполнение
    :if ([:len $NewDuration] = 0) do={
        :log info "Насос - Длительность не установлена"
    } else={
        # Проверка типа данных команды
        :if ([:typeof $NewDuration] = "num") do={
            :local poeStatus [/interface ethernet get [find name=$PoeMainInterface] poe-out]
            # Команда остановки насоса (NewDuration = 0)
            :if ($NewDuration = 0) do={
                :log warning ("Насос - ОТЛАДКА: Текущий статус POE = [" . $poeStatus . "]")
                # Проверка текущего статуса POE перед отключением
                :if ($poeStatus != "off") do={
                    # Физическое отключение POE
                    /interface ethernet poe set $PoeMainInterface poe-out=off
                    :log warning "Насос - POE ФИЗИЧЕСКИ ОТКЛЮЧЕН"
                # Расчет времени работы насоса с помощью TimeUtils
                :local workTimeMsg ""
                :if ([:len $PoeStartTime] > 0) do={
                    :local currentTime [/system clock get time]
                    :log info ("Насос - TimeUtils: PoeStartTime=" . $PoeStartTime . ", currentTime=" . $currentTime)
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
                    :log info ("Насос - TimeUtils: Вычислено workSeconds=" . $workSeconds)
                    # Использование TimeUtils для форматирования
                    :set InputSeconds $workSeconds
                    :log info ("Насос - TimeUtils: Установлено InputSeconds=" . $InputSeconds)
                    /system script run Nasos-TimeUtils
                    :log info ("Насос - TimeUtils: Результат FormattedLog=" . $FormattedLog)
                    :set workTimeMsg (" " . $FormattedLog)
                    :log info ("Насос - TimeUtils: Итоговое workTimeMsg=" . $workTimeMsg)
                }
                # Сохранение времени остановки
                :set LastStopTime [/system clock get time]
                :local logMsg "Насос - НАСОС ОСТАНОВЛЕН ПО КОМАНДЕ"
                :set logMsg ($logMsg . $workTimeMsg)
                :log warning $logMsg
                # Формирование Telegram сообщения с временем работы
                :local telegramWorkMsg ""
                :if ([:len $PoeStartTime] > 0) do={
                    :local currentTime [/system clock get time]
                    :log info ("Насос - TimeUtils Telegram: PoeStartTime=" . $PoeStartTime . ", currentTime=" . $currentTime)
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
                    :log info ("Насос - TimeUtils Telegram: Вычислено workSeconds=" . $workSeconds)
                    # Использование TimeUtils для Telegram форматирования
                    :set InputSeconds $workSeconds
                    :log info ("Насос - TimeUtils Telegram: Установлено InputSeconds=" . $InputSeconds)
                    /system script run Nasos-TimeUtils
                    :log info ("Насос - TimeUtils Telegram: Результат FormattedTelegram=" . $FormattedTelegram)
                    :set telegramWorkMsg ($MsgTimeWorkedHeader . " " . $FormattedTelegram)
                    :log info ("Насос - TimeUtils Telegram: Итоговое telegramWorkMsg=" . $telegramWorkMsg)
                    # Сохранение длительности работы
                    :set LastWorkDuration $workSeconds
                    :log info ("Насос - Сохранена длительность работы: " . $LastWorkDuration . " сек.")
                }
                # Получение времени остановки
                :local stopTime [/system clock get time]
                # Отправка уведомления в Telegram
                :local telegramMsg ($MsgStatusHeader . " " . $MsgPumpStoppedByCmd . $MsgNewLine . $telegramWorkMsg . $MsgNewLine . "%F0%9F%95%90%20%D0%9E%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%20%D0%B2%3A%20" . $stopTime)
                $sendTelegram $BotToken $ChatId $telegramMsg
                # Удаление активного таймера
                :if ([:len $PoeActiveTimer] > 0) do={
                    :if ([:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
                        /system scheduler remove [find name=$PoeActiveTimer]
                        :log warning ("Насос - Удален активный таймер: " . $PoeActiveTimer)
                    }
                    :set PoeActiveTimer ""
                }
                # Очистка старых таймеров
                :foreach timer in=[/system scheduler find where name~"poe-timer"] do={
                    :local timerName [/system scheduler get $timer name]
                    /system scheduler remove $timer
                    :log warning ("Насос - Удален старый таймер: " . $timerName)
                }
                # Очистка переменных состояния
                :set PoeStartTime ""
                :set NewDuration ""
                } else={
                    # Насос уже отключен - показываем время с момента отключения
                    :local timeSinceStopMsg ""
                    :if ([:len $LastStopTime] > 0) do={
                        :local currentTime [/system clock get time]
                        :local stopHours [:pick $LastStopTime 0 2]
                        :local stopMinutes [:pick $LastStopTime 3 5]
                        :local stopSecs [:pick $LastStopTime 6 8]
                        :local stopSeconds ($stopHours * 3600 + $stopMinutes * 60 + $stopSecs)
                        :local currentHours [:pick $currentTime 0 2]
                        :local currentMins [:pick $currentTime 3 5]
                        :local currentSecs [:pick $currentTime 6 8]
                        :local currentSeconds ($currentHours * 3600 + $currentMins * 60 + $currentSecs)
                        :local timeSinceStop ($currentSeconds - $stopSeconds)
                        :if ($timeSinceStop < 0) do={
                            :set timeSinceStop ($timeSinceStop + 86400)
                        }
                        :local stopMinutes ($timeSinceStop / 60)
                        :local stopSecondsRem ($timeSinceStop - ($stopMinutes * 60))
                        :set timeSinceStopMsg ($MsgTimeSinceStop . " " . [:tostr $stopMinutes] . $MsgTimeMin . [:tostr $stopSecondsRem] . $MsgTimeSec)
                    }
                    :log warning ("Насос - НАСОС УЖЕ ОТКЛЮЧЕН" . $timeSinceStopMsg)
                    :local telegramMsg ($MsgHeader . $MsgNewLine . $MsgStatusHeader . $MsgNewLine . $MsgPumpAlreadyStopped . $timeSinceStopMsg)
                    $sendTelegram $BotToken $ChatId $telegramMsg
                    # Очистка переменной команды
                    :set NewDuration ""
                }
            } else={
                # Команда уменьшения времени работы (NewDuration < 0)
                :if ($NewDuration < 0) do={
                    :if ([:len $PoeActiveTimer] > 0) do={
                        # Получение текущего интервала таймера
                        :local currentInterval [/system scheduler get [find name=$PoeActiveTimer] interval]
                        :local intervalHours [:pick $currentInterval 0 2]
                        :local intervalMins [:pick $currentInterval 3 5]
                        :local intervalSecs [:pick $currentInterval 6 8]
                        :local currentIntervalSeconds ($intervalHours * 3600 + $intervalMins * 60 + $intervalSecs)
                        # Расчет времени работы
                        :local workSeconds 0
                        :if ([:len $PoeStartTime] > 0) do={
                            :local currentTime [/system clock get time]
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
                        # Расчет нового времени работы
                        :local remainingSeconds ($currentIntervalSeconds - $workSeconds)
                        :local newRemainingSeconds ($remainingSeconds + $NewDuration)
                        # Проверка на превышение времени
                        :if ($newRemainingSeconds <= 0) do={
                            # Немедленная остановка - время истекло
                            :local workTimeMsg ""
                            :if ([:len $PoeStartTime] > 0) do={
                                :local currentTime [/system clock get time]
                                :local startHours [:pick $PoeStartTime 0 2]
                                :local startMinutes [:pick $PoeStartTime 3 5]
                                :local startSecs [:pick $PoeStartTime 6 8]
                                :local hoursToSecs2 ($startHours * 3600)
                                :local minsToSecs2 ($startMinutes * 60)
                                :local startSeconds ($hoursToSecs2 + $minsToSecs2 + $startSecs)
                                :local currentHours [:pick $currentTime 0 2]
                                :local currentMins [:pick $currentTime 3 5]
                                :local currentSecs [:pick $currentTime 6 8]
                                :local currentHoursToSecs2 ($currentHours * 3600)
                                :local currentMinsToSecs2 ($currentMins * 60)
                                :local currentSeconds ($currentHoursToSecs2 + $currentMinsToSecs2 + $currentSecs)
                                :local workSeconds ($currentSeconds - $startSeconds)
                                :if ($workSeconds < 0) do={
                                    :set workSeconds ($workSeconds + 86400)
                                }
                                :local workMinutes ($workSeconds / 60)
                                :local workSecondsRem ($workSeconds - ($workMinutes * 60))
                                :set workTimeMsg ($MsgTimeWorkedTemplate . [:tostr $workMinutes] . $MsgTimeMin . [:tostr $workSecondsRem] . $MsgTimeSec)
                            }
                            # Отправка уведомления об автоматической остановке
                            $sendTelegram $BotToken $ChatId ($MsgSysStarted . $MsgNewLine . $MsgStatusCurrent . $MsgNewLine . $MsgPumpAutoStop . $workTimeMsg)
                            :set LastStopTime [/system clock get time]
                            # Сохранение длительности работы
                            :set LastWorkDuration $workSeconds
                            :log info ("Насос - Сохранена длительность работы при уменьшении времени: " . $LastWorkDuration . " сек.")
                            :local logMsg "Насос - НАСОС ОСТАНОВЛЕН - время уменьшено"
                            :set logMsg ($logMsg . $workTimeMsg)
                            :log warning $logMsg
                            # Формирование Telegram сообщения
                            :local telegramWorkMsg ""
                            :if ([:len $PoeStartTime] > 0) do={
                                :local workMinutes ($workSeconds / 60)
                                :local workSecondsRem ($workSeconds - ($workMinutes * 60))
                                :set telegramWorkMsg ($MsgTimeWorkedHeader . " " . [:tostr $workMinutes] . $MsgTimeMin . [:tostr $workSecondsRem] . $MsgTimeSec)
                            }
                            :local telegramMsg ($MsgHeader . $MsgNewLine . $MsgStatusHeader . $MsgNewLine . $MsgPumpStoppedTimeReduced . $telegramWorkMsg)
                            $sendTelegram $BotToken $ChatId $telegramMsg
                            # Удаление таймера и очистка переменных
                            :if ([:len $PoeActiveTimer] > 0) do={
                                :if ([:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
                                    /system scheduler remove [find name=$PoeActiveTimer]
                                    :log warning ("Насос - Удален старый таймер: " . $PoeActiveTimer)
                                }
                            }
                            :set PoeActiveTimer ""
                            :set PoeStartTime ""
                            :set NewDuration ""
                        } else={
                            # Обновление таймера с новым интервалом
                            :local newTotalSeconds ($workSeconds + $newRemainingSeconds)
                            :local newIntervalHours ($newRemainingSeconds / 3600)
                            :local newIntervalMins (($newRemainingSeconds - ($newIntervalHours * 3600)) / 60)
                            :local newIntervalSecsRem ($newRemainingSeconds - ($newIntervalHours * 3600) - ($newIntervalMins * 60))
                            # Форматирование времени
                            :if ($newIntervalHours < 10) do={ :set newIntervalHours ("0" . $newIntervalHours) }
                            :if ($newIntervalMins < 10) do={ :set newIntervalMins ("0" . $newIntervalMins) }
                            :if ($newIntervalSecsRem < 10) do={ :set newIntervalSecsRem ("0" . $newIntervalSecsRem) }
                            :local newInterval ($newIntervalHours . ":" . $newIntervalMins . ":" . $newIntervalSecsRem)
                            # Обновление таймера
                            /system scheduler set [find name=$PoeActiveTimer] interval=$newInterval
                            # Расчет уменьшенного времени для отчета
                            :local reducedSecs (0 - $NewDuration)
                            :local reducedMinutes ($reducedSecs / 60)
                            :local reducedSecondsRem ($reducedSecs - ($reducedMinutes * 60))
                            :local totalMinutes ($newTotalSeconds / 60)
                            :local totalSecondsRem ($newTotalSeconds - ($totalMinutes * 60))
                            :local workMinutes ($workSeconds / 60)
                            :local workSecondsRem ($workSeconds - ($workMinutes * 60))
                            # Формирование сообщений
                            :local msg1 ($MsgTimeReduced . " " . $reducedMinutes . $MsgTimeMin . $reducedSecondsRem . $MsgTimeSec)
                            :local msg2 ($MsgNewLine . $MsgTimeWorked . $workMinutes . $MsgTimeMin . $workSecondsRem . $MsgTimeSec)
                            :local msg3 ($MsgTimeExpectedTotal . " " . $totalMinutes . $MsgTimeMin . $totalSecondsRem . $MsgTimeSec)
                            :local fullMsg ($msg1 . $msg2)
                            :log warning $fullMsg
                            :log warning $msg3
                            # Отправка уведомлений в Telegram
                            :local telegramWorkMsg ($MsgTimeAlreadyWorkedTranslit . [:tostr $workMinutes] . " minut " . [:tostr $workSecondsRem] . " sekund")
                            :local telegramMsg ($MsgTimeReduced . " " . $reducedMinutes . $MsgTimeMin . $reducedSecondsRem . $MsgTimeSec . $telegramWorkMsg)
                            $sendTelegram $BotToken $ChatId $telegramMsg
                            :local telegramTotalMsg ($MsgTimeExpectedTotal . " " . $totalMinutes . $MsgTimeMin . $totalSecondsRem . $MsgTimeSec)
                            $sendTelegram $BotToken $ChatId $telegramTotalMsg
                            :set NewDuration ""
                        }
                    } else={
                        # Ошибка - нет активного таймера
                        :log error "Насос - Нет активного таймера"
                        $sendTelegram $BotToken $ChatId ($MsgSysStarted . $MsgNewLine . $MsgSysError . "%D0%9D%D0%B5%D1%82%20%D0%B0%D0%BA%D1%82%D0%B8%D0%B2%D0%BD%D0%BE%D0%B3%D0%BE%20%D1%82%D0%B0%D0%B9%D0%BC%D0%B5%D1%80%D0%B0")
                        :set NewDuration ""
                    }
                } else={
                    # Команда запуска или продления работы насоса (NewDuration > 0)
                    :if ($NewDuration > 0) do={
                        :local durationMinutes ($NewDuration / 60)
                        :local durationSeconds ($NewDuration - ($durationMinutes * 60))
                        # Используем TimeUtils для красивого форматирования
                        :set InputSeconds $NewDuration
                        /system script run Nasos-TimeUtils
                        :local durationFormatted $FormattedTelegram
                        # Проверка текущего состояния насоса
                        :if ($poeStatus = "forced-on") do={
                            # Насос уже работает - продление времени работы
                            :local workTimeMsg ""
                            :local workSeconds 0
                            :if ([:len $PoeStartTime] > 0) do={
                                :local currentTime [/system clock get time]
                                :local startHours [:pick $PoeStartTime 0 2]
                                :local startMinutes [:pick $PoeStartTime 3 5]
                                :local startSecs [:pick $PoeStartTime 6 8]
                                :local hoursToSecs3 ($startHours * 3600)
                                :local minsToSecs3 ($startMinutes * 60)
                                :local startSeconds ($hoursToSecs3 + $minsToSecs3 + $startSecs)
                                :local currentHours [:pick $currentTime 0 2]
                                :local currentMins [:pick $currentTime 3 5]
                                :local currentSecs [:pick $currentTime 6 8]
                                :local currentHoursToSecs3 ($currentHours * 3600)
                                :local currentMinsToSecs3 ($currentMins * 60)
                                :local currentSeconds ($currentHoursToSecs3 + $currentMinsToSecs3 + $currentSecs)
                                :set workSeconds ($currentSeconds - $startSeconds)
                                :if ($workSeconds < 0) do={
                                    :set workSeconds ($workSeconds + 86400)
                                }
                                :local workMinutes ($workSeconds / 60)
                                :local workSecondsRem ($workSeconds - ($workMinutes * 60))
                                :set workTimeMsg ($MsgTimeAlreadyWorkedTemplate . [:tostr $workMinutes] . $MsgTimeMin . [:tostr $workSecondsRem] . $MsgTimeSec)
                            }
                            # Логирование продления работы
                            :local logMsg ("Насос - НАСОС УЖЕ РАБОТАЕТ - будет работать еще" . " " . $durationMinutes . " минут " . $durationSeconds . " секунд")
                            :set logMsg ($logMsg . $workTimeMsg)
                            :log warning $logMsg
                            # Расчет общего ожидаемого времени работы
                            :local totalExpectedTime ($workSeconds + $NewDuration)
                            :local totalExpectedMinutes ($totalExpectedTime / 60)
                            :local totalExpectedSeconds ($totalExpectedTime - ($totalExpectedMinutes * 60))
                            :log warning ($MsgTimeExpectedTotal . " " . $totalExpectedMinutes . $MsgTimeMin . $totalExpectedSeconds . $MsgTimeSec)
                            # Отправка уведомления в Telegram (используем TimeUtils)
                            # Форматируем время работы через TimeUtils
                            :set InputSeconds $workSeconds
                            /system script run Nasos-TimeUtils
                            :local telegramWorkMsg ($MsgTimeWorkedHeader . " " . $FormattedTelegram)
                            # Форматируем ожидаемое общее время через TimeUtils
                            :set InputSeconds $totalExpectedTime
                            /system script run Nasos-TimeUtils
                            :local telegramTotalMsg ($MsgTimeExpectedTotal . " " . $FormattedTelegram)
                            :local telegramMsg ($MsgStatusHeader . " " . $MsgPumpAlreadyOn . $MsgNewLine . $MsgTimeRemaining . " " . $durationFormatted . $MsgNewLine . $telegramWorkMsg . $MsgNewLine . $telegramTotalMsg)
                            $sendTelegram $BotToken $ChatId $telegramMsg
                            # Создание нового таймера с продленным временем
                            :local intervalHours ($NewDuration / 3600)
                            :local intervalMins (($NewDuration - ($intervalHours * 3600)) / 60)
                            :local intervalSecs ($NewDuration - ($intervalHours * 3600) - ($intervalMins * 60))
                            :if ($intervalHours < 10) do={ :set intervalHours ("0" . $intervalHours) }
                            :if ($intervalMins < 10) do={ :set intervalMins ("0" . $intervalMins) }
                            :if ($intervalSecs < 10) do={ :set intervalSecs ("0" . $intervalSecs) }
                            :local newInterval ($intervalHours . ":" . $intervalMins . ":" . $intervalSecs)
                            # Удаление старого таймера
                            :if ([:len $PoeActiveTimer] > 0) do={
                                :if ([:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
                                    /system scheduler remove [find name=$PoeActiveTimer]
                                    :log warning ("Насос - Удален старый таймер: " . $PoeActiveTimer)
                                }
                            }
                            # Создание нового таймера
                            :local timerName $PoeTimerName
                            /system scheduler add name=$timerName interval=$newInterval on-event=$MsgStopCmdTemplate
                            :set PoeActiveTimer $timerName
                            :log warning ("Насос - Создан новый таймер: " . $timerName . " с интервалом: " . $newInterval)
                        } else={
                            # Запуск насоса
                            /interface ethernet set [find name=$PoeMainInterface] poe-out=forced-on
                            :set PoeStartTime [/system clock get time]
                            :local logMsg ("Насос - НАСОС ЗАПУЩЕН на " . $durationMinutes . " минут " . $durationSeconds . " секунд")
                            :log warning $logMsg
                            # Отправка уведомления о запуске (используем TimeUtils)
                            :local telegramMsg ($MsgHeader . $MsgNewLine . $MsgStatusHeader . $MsgNewLine . $MsgPumpStartedFor . " " . $durationFormatted)
                            $sendTelegram $BotToken $ChatId $telegramMsg
                            # Создание таймера остановки
                            :local intervalHours ($NewDuration / 3600)
                            :local intervalMins (($NewDuration - ($intervalHours * 3600)) / 60)
                            :local intervalSecs ($NewDuration - ($intervalHours * 3600) - ($intervalMins * 60))
                            :if ($intervalHours < 10) do={ :set intervalHours ("0" . $intervalHours) }
                            :if ($intervalMins < 10) do={ :set intervalMins ("0" . $intervalMins) }
                            :if ($intervalSecs < 10) do={ :set intervalSecs ("0" . $intervalSecs) }
                            :local schedulerInterval ($intervalHours . ":" . $intervalMins . ":" . $intervalSecs)
                            # Удаление старых таймеров
                            :if ([:len $PoeActiveTimer] > 0) do={
                                :if ([:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
                                    /system scheduler remove [find name=$PoeActiveTimer]
                                    :log warning ("Насос - Удален старый таймер: " . $PoeActiveTimer)
                                }
                            }
                            # Создание нового таймера
                            :local timerName $PoeTimerName
                            /system scheduler add name=$timerName interval=$schedulerInterval on-event=$MsgStopCmdTemplate
                            :set PoeActiveTimer $timerName
                            :log warning ("Насос - Создан новый таймер: " . $timerName . " с интервалом: " . $schedulerInterval)
                        }
                        # Очистка команды
                        :set NewDuration ""
                    }
                }
            }
        } else={
            # Ошибка типа данных
            :log error "Насос - Длительность должна быть числом"
        }
    }
}
