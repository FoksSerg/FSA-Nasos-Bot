# ===== NASOS TELEGRAM POLLER =====
# Безопасный опрос Telegram API с обработкой ошибок
# Автор: Фокин Сергей Александрович foks_serg@mail.ru  
# Дата создания: 23 июня 2025
# Версия: 1.0 - Отказоустойчивый опрос команд

# Объявление глобальных переменных для работы с API
:global BotToken; :global ChatId; :global LastUpdateId

# Переменные состояния опроса
# TgLastCommand - Последняя полученная команда
# TgCommandTime - Время получения команды  
# TgPollStatus - Статус последнего опроса (ok/error)
# TgPollError - Описание последней ошибки
# TgPollHeartbeat - Время последнего успешного опроса
# TgStartMinutes - Количество минут для универсальной команды start
:global TgLastCommand
:global TgCommandTime
:global TgPollStatus
:global TgPollError
:global TgPollHeartbeat
:global TgStartMinutes

# Проверка критичных переменных
:if ([:len $BotToken] = 0 || [:len $ChatId] = 0) do={
    :set TgPollStatus "error"
    :set TgPollError "Не заданы BotToken или ChatId"
    :log error ("TG-Poller: " . $TgPollError)
    :return false
}

# Инициализация LastUpdateId если не задан
:if ([:typeof $LastUpdateId] = "nothing" || [:len $LastUpdateId] = 0) do={
    :set LastUpdateId 1
}

# Безопасный опрос API с обработкой ошибок
:local pollSuccess false
:local content ""
:local errorMessage ""

:do {
    # Формирование URL для опроса
    :local getUrl ("https://api.telegram.org/bot" . $BotToken . "/getUpdates?limit=5&offset=" . $LastUpdateId)
    
    # Выполнение запроса с таймаутом
    :local updates [/tool fetch url=$getUrl as-value output=user]
    :set content ($updates->"data")
    
    # Проверка наличия данных
    :if ([:len $content] > 10) do={
        :set pollSuccess true
    } else={
        :set pollSuccess true
    }
    
} on-error={
    :set errorMessage "Ошибка запроса к Telegram API"
    :log error ("TG-Poller: " . $errorMessage)
}

# Обработка результатов опроса
:if ($pollSuccess) do={
    :set TgPollStatus "ok"
    :set TgPollError ""
    :set TgPollHeartbeat [/system clock get time]
    
    # Обработка полученных данных только если есть контент
    :if ([:len $content] > 10) do={
        
        # Обновление offset
        :local updateIdPos [:find $content "\"update_id\":"]
        :if ([:len $updateIdPos] > 0) do={
            :local idStart ($updateIdPos + 12)
            :local idEnd [:find $content "," $idStart]
            :local newUpdateId [:pick $content $idStart $idEnd]
            :set LastUpdateId ($newUpdateId + 1)
        }
        
        # Поиск команд в контенте
        :local detectedCommand ""
        
        # Проверка команд
        :if ([:len [:find $content "\"/stop\""]] > 0 || [:len [:find $content "\"stop\""]] > 0) do={
            :set detectedCommand "stop"
        }
        :if ([:len [:find $content "\"/status\""]] > 0 || [:len [:find $content "\"status\""]] > 0) do={
            :set detectedCommand "status"  
        }
        :if ([:len [:find $content "\"/menu\""]] > 0 || [:len [:find $content "\"menu\""]] > 0) do={
            :set detectedCommand "menu"
        }
        
        # Универсальная команда /start с произвольным числом минут
        :if ([:len $detectedCommand] = 0) do={
            # Поиск паттернов /startЧЧ, /start ЧЧ, startЧЧ, start ЧЧ
            :local startPos1 [:find $content "\"/start"]
            :local startPos2 [:find $content "\"start"]
            :local startPos 0
            :local hasSpace false
            
            :if ([:len $startPos1] > 0) do={
                :set startPos ($startPos1 + 7)
                # Проверяем есть ли пробел после /start
                :local nextChar [:pick $content $startPos ($startPos + 1)]
                :if ($nextChar = " ") do={
                    :set hasSpace true
                    :set startPos ($startPos + 1)
                }
            }
            :if ([:len $startPos2] > 0 && [:len $startPos1] = 0) do={
                :set startPos ($startPos2 + 6)
                # Проверяем есть ли пробел после start
                :local nextChar [:pick $content $startPos ($startPos + 1)]
                :if ($nextChar = " ") do={
                    :set hasSpace true
                    :set startPos ($startPos + 1)
                }
            }
            
            :if ($startPos > 0) do={
                # Извлечение числа после start (может быть отрицательным)
                :local endPos [:find $content "\"" $startPos]
                :if ([:len $endPos] > 0) do={
                    :local minutesStr [:pick $content $startPos $endPos]
                    # Проверка что это число (включая отрицательные и ноль)
                    :if ([:len $minutesStr] > 0 && [:len $minutesStr] < 6) do={
                        :local minutes [:tonum $minutesStr]
                        # Принимаем любые числа от -999 до 999 (включая 0)
                        :if ($minutes >= -999 && $minutes <= 999) do={
                            :set detectedCommand "start"
                            :set TgStartMinutes $minutes
                        }
                    }
                }
            }
        }
        
        # Сохранение найденной команды
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
 