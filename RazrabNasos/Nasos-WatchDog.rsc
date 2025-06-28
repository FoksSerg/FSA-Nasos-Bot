# ===== NASOS WATCHDOG =====
# Модуль мониторинга и перезапуска Telegram бота при зависании
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 15 июня 2025
# Версия: 1.3 - Использование Nasos-TG-Activator для надежной отправки сообщений

# Объявление глобальных переменных
:global NasosInitStatus
:global BotToken
:global ChatId
:global TelegramHeartbeat
:global MsgNewLine
:global MsgSysWatchdogTimeout
:global MsgSysWatchdogMin
:global MsgSysWatchdogRestart
:global MsgTimeMin
:global TgAction
:global TgMessage
:global TgCleanupTime

# Проверка инициализации системы
:if ([:typeof $NasosInitStatus] = "nothing" || !$NasosInitStatus) do={
    :log warning "Насос - Запуск Nasos-Init"
    /system script run Nasos-Init
}

# Получение текущего времени и установка таймаута
:local currentTime [/system clock get time]
:local timeoutMinutes 10

# Проверка наличия heartbeat от Telegram модуля
:if ([:len $TelegramHeartbeat] > 0) do={
    # Парсинг времени последнего heartbeat
    :local heartbeatHours [:pick $TelegramHeartbeat 0 2]
    :local heartbeatMins [:pick $TelegramHeartbeat 3 5]
    :local heartbeatSecs [:pick $TelegramHeartbeat 6 8]
    :local heartbeatSeconds ($heartbeatHours * 3600 + $heartbeatMins * 60 + $heartbeatSecs)
    
    # Парсинг текущего времени
    :local currentHours [:pick $currentTime 0 2]
    :local currentMins [:pick $currentTime 3 5]
    :local currentSecs [:pick $currentTime 6 8]
    :local currentSeconds ($currentHours * 3600 + $currentMins * 60 + $currentSecs)
    
    # Расчет разности времени
    :local timeDiff ($currentSeconds - $heartbeatSeconds)
    :if ($timeDiff < 0) do={
        :set timeDiff ($timeDiff + 86400)
    }
    :local diffMinutes ($timeDiff / 60)
    
    # Проверка превышения таймаута
    :if ($diffMinutes > $timeoutMinutes) do={
        :log error ("Насос - Telegram парсер не отвечает " . $diffMinutes . " минут - перезапуск")
        
        # Отправка уведомления о перезапуске через активатор
        :local alertMsg ($MsgSysWatchdogTimeout . $diffMinutes . $MsgTimeMin)
        :set TgAction "send"
        :set TgMessage $alertMsg
        :set TgCleanupTime "30"
        /system script run Nasos-TG-Activator
        :log info "Насос - Отправлено уведомление о таймауте через TG-Activator"
        
        # Завершение существующего процесса Telegram
        :if ([:len [/system script job find script="Nasos-Telegram"]] > 0) do={
            /system script job remove [find script="Nasos-Telegram"]
            :log warning "Насос - Завершен существующий процесс Nasos-Telegram"
        }
        
        # Пауза перед перезапуском
        :delay 2s
        
        # Перезапуск модуля Telegram
        /system script run Nasos-Telegram
        :log warning "Насос - Перезапущен скрипт Nasos-Telegram"
    }
} else={
    # Heartbeat не найден - первый запуск или сбой
    :log warning "Насос - Heartbeat не найден - запуск Nasos-Telegram"
    
    # Отправка уведомления о перезапуске через активатор
    :set TgAction "send"
    :set TgMessage $MsgSysWatchdogRestart
    :set TgCleanupTime "30"
    /system script run Nasos-TG-Activator
    :log info "Насос - Отправлено уведомление о перезапуске через TG-Activator"
    
    /system script run Nasos-Telegram
} 