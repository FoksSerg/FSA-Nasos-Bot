# ===== NASOS TELEGRAM ACTIVATOR =====
# Активатор действий с Telegram API через scheduler
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 22 июня 2025
# Версия: 1.0

# Объявление глобальных переменных
:global TgAction
:global TgMessage
:global TgCleanupTime

:log warning "TG-Activator: Запуск активатора Telegram"

# Проверка наличия параметров
:if ([:len $TgAction] = 0 && [:len $TgMessage] = 0) do={
    :log error "TG-Activator: Не заданы параметры для активации (TgAction или TgMessage)"
    :log info "TG-Activator: Использование: :global TgAction \"send|clear|set\"; :global TgMessage \"текст\""
    :log info "TG-Activator: Завершение работы без выполнения действий"
} else={
    # Определение действия по умолчанию
    :local action "send"
    :if ([:len $TgAction] > 0) do={
        :set action $TgAction
    }

    # Определение времени жизни scheduler (по умолчанию 30 секунд)
    :local cleanupTime 30
    :if ([:len $TgCleanupTime] > 0) do={
        :set cleanupTime $TgCleanupTime
    }

    # Определение имени скрипта для запуска
    :local targetScript ""
    :local actionValid 1
    
    :if ($action = "send") do={
        :if ([:len $TgMessage] > 0) do={
            :set targetScript "Nasos-TG-SendMessage"
            :log info ("TG-Activator: Активация отправки сообщения: " . $TgMessage)
        } else={
            :log error "TG-Activator: Для действия 'send' требуется задать TgMessage"
            :set actionValid 0
        }
    }
    :if ($action = "clear") do={
        :set targetScript "Nasos-TG-MenuClear"
        :log info ("TG-Activator: Активация очистки меню")
    }
    :if ($action = "set") do={
        :set targetScript "Nasos-TG-MenuSet"
        :log info ("TG-Activator: Активация установки меню")
    }
    :if ($action = "keyboard") do={
        :if ([:len $TgMessage] > 0) do={
            :set targetScript "Nasos-TG-SendKeyboard"
            :log info ("TG-Activator: Активация отправки inline клавиатуры: " . $TgMessage)
        } else={
            :log error "TG-Activator: Для действия 'keyboard' требуется задать TgMessage"
            :set actionValid 0
        }
    }
    :if ($action = "replykeyboard") do={
        :if ([:len $TgMessage] > 0) do={
            :set targetScript "Nasos-TG-SendReplyKeyboard"
            :log info ("TG-Activator: Активация отправки reply клавиатуры: " . $TgMessage)
        } else={
            :log error "TG-Activator: Для действия 'replykeyboard' требуется задать TgMessage"
            :set actionValid 0
        }
    }

    # Проверка корректности действия
    :if ([:len $targetScript] = 0 && $actionValid = 1) do={
        :log error ("TG-Activator: Неизвестное действие: " . $action)
        :set actionValid 0
    }

    # Продолжение работы только при корректном действии
    :if ($actionValid = 1) do={
        # Генерация уникального имени scheduler
        :local timestamp [:timestamp]
        :local schedName ("tg-sched-" . $action . "-" . $timestamp)

        # Удаление существующих scheduler с похожими именами (безопасность)
        :foreach i in=[/system scheduler find where name~"tg-sched-"] do={
            :local schedAge ([:timestamp] - [/system scheduler get $i start-time])
            :if ($schedAge > 300) do={
                :local oldName [/system scheduler get $i name]
                /system scheduler remove $i
                :log warning ("TG-Activator: Удален старый scheduler: " . $oldName)
            }
        }

        # Простое вычисление времени запуска (текущее время + 1 секунда)
        :local currentTime [/system clock get time]
        :local hours [:tonum [:pick $currentTime 0 2]]
        :local minutes [:tonum [:pick $currentTime 3 5]]
        :local seconds [:tonum [:pick $currentTime 6 8]]
        
        # Добавляем 1 секунду
        :set seconds ($seconds + 1)
        :if ($seconds >= 60) do={
            :set seconds ($seconds - 60)
            :set minutes ($minutes + 1)
            :if ($minutes >= 60) do={
                :set minutes ($minutes - 60)
                :set hours ($hours + 1)
                :if ($hours >= 24) do={
                    :set hours ($hours - 24)
                }
            }
        }
        
        # Форматирование времени
        :local startTime ([:tostr $hours] . ":" . [:tostr $minutes] . ":" . [:tostr $seconds])
        :log info ("TG-Activator: Время запуска scheduler: " . $startTime)

        # Создание команды для scheduler
        :local schedCommand ("/system script run " . $targetScript)

        # Создание scheduler с конкретным временем запуска
        :log info ("TG-Activator: Создание scheduler: " . $schedName)
        /system scheduler add name=$schedName start-time=$startTime interval=0 on-event=$schedCommand

        # Создание cleanup scheduler для автоудаления
        :local cleanupSchedName ($schedName . "-cleanup")
        :local cleanupCommand ("/system scheduler remove [find name=" . $schedName . "]; /system scheduler remove [find name=" . $cleanupSchedName . "]")

        :log info ("TG-Activator: Создание cleanup scheduler: " . $cleanupSchedName . " (удаление через " . $cleanupTime . "s)")
        /system scheduler add name=$cleanupSchedName start-time=$startTime interval=$cleanupTime on-event=$cleanupCommand

        :log info ("TG-Activator: Активация завершена. Scheduler " . $schedName . " запустится в " . $startTime)
    } else={
        :log error "TG-Activator: Активация прервана из-за ошибки"
        # Очистка переменных только при ошибке
        :set TgAction ""
        :set TgMessage ""
        :set TgCleanupTime ""
    }
}

:log info "TG-Activator: Завершение работы активатора" 