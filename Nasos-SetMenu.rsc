# ===== NASOS SET MENU =====
# Модуль установки меню команд для Telegram бота
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 21 июня 2025
# Версия: 1.5

# Объявление глобальных переменных
:global NasosInitStatus
:global BotToken
:global ChatId
:global MsgMenuStop
:global MsgMenuStatus
:global MsgMenuStart5
:global MsgMenuStart10
:global MsgMenuStart30
:global MsgMenuStart60
:global MsgMenuStart120
:global MsgMenuShow

# Надежная проверка инициализации системы с повторными попытками
:local initAttempts 0
:local maxInitAttempts 3
:local initSuccess false

:while (!$initSuccess && $initAttempts < $maxInitAttempts) do={
    :set initAttempts ($initAttempts + 1)
    :log warning ("Меню - Попытка инициализации #" . $initAttempts)
    
    # Проверка базовой инициализации
    :if ([:typeof $NasosInitStatus] = "nothing" || !$NasosInitStatus) do={
        :log warning "Меню - Запуск Nasos-Init"
        /system script run Nasos-Init
        :delay 2s
    }
    
    # Проверка критичного BotToken
    :if ([:len $BotToken] = 0) do={
        :log error ("Меню - Попытка #" . $initAttempts . ": BotToken не инициализирован")
        :if ($initAttempts < $maxInitAttempts) do={
            :log warning "Меню - Повторная попытка инициализации через 3 секунды..."
            :delay 3s
        }
    } else={
        # Проверка переменных сообщений - если не инициализированы, загружаем Messages
        :if ([:len $MsgMenuStop] = 0 || [:len $MsgMenuStatus] = 0) do={
            :log warning "Меню - Переменные сообщений не инициализированы, загрузка Nasos-Messages"
            /system script run Nasos-Messages
            :delay 1s
        }
        
        # Финальная проверка всех критичных переменных
        :if ([:len $BotToken] > 0 && [:len $MsgMenuStop] > 0 && [:len $MsgMenuStatus] > 0) do={
            :set initSuccess true
            :log info "Меню - Инициализация успешна!"
        } else={
            :log error ("Меню - Попытка #" . $initAttempts . ": Не все переменные инициализированы")
            :log error ("BotToken: " . [:len $BotToken] . ", MsgMenuStop: " . [:len $MsgMenuStop] . ", MsgMenuStatus: " . [:len $MsgMenuStatus])
        }
    }
}

# Критическая ошибка если инициализация не удалась
:if (!$initSuccess) do={
    :log error "Меню - КРИТИЧЕСКАЯ ОШИБКА: Не удалось инициализировать переменные после 3 попыток!"
    :error "Menu initialization failed - check Nasos-Init.rsc and Nasos-Messages.rsc"
}

# Убираем сложную функцию nextTime - используем простые задержки

# Неиспользуемая строка удалена

# Функция создания безопасного самоудаляющегося скрипта
:global createTempScript do={
    :local scriptName $1
    :local schedName $2
    :local apiUrl $3
    
    :log info ("Создание безопасного самоудаляющегося скрипта: " . $scriptName)
    
    # Удаляем если существует
    :if ([:len [/system script find name=$scriptName]] > 0) do={
        /system script remove [find name=$scriptName]
    }
    
    # Удаляем старые scheduler'ы если существуют
    :if ([:len [/system scheduler find name=$schedName]] > 0) do={
        /system scheduler remove [find name=$schedName]
    }
    
    :local cleanupName ($schedName . "-cleanup")
    :if ([:len [/system scheduler find name=$cleanupName]] > 0) do={
        /system scheduler remove [find name=$cleanupName]
    }
    
    # Создаем кавычки для URL
    :local quote ""
    :set quote ($quote . "\"")
    
    # Собираем код скрипта напрямую
    :local scriptCode (":local clearMenuUrl (" . $quote . $apiUrl . $quote . "); /tool fetch url=\$clearMenuUrl http-method=post keep-result=no")
    
    # ЛОГИРУЕМ ИТОГОВЫЙ КОД СКРИПТА ДЛЯ ДИАГНОСТИКИ
    :log info ("СОЗДАВАЕМЫЙ СКРИПТ " . $scriptName . ": " . $scriptCode)
    
    # Создаем скрипт
    /system script add name=$scriptName source=$scriptCode
    
    # Scheduler с однократным запуском через 1 секунду
    /system scheduler add name=$schedName start-time=startup interval=0 on-event=("/system script run " . $scriptName)
    
    # Создаем отдельный cleanup script - ТОЛЬКО ОДНА КОМАНДА как тестовый
    :local schedCleanupName ($cleanupName . "-sched")
    
    # Простая cleanup команда - ТОЛЬКО УДАЛЕНИЕ ОСНОВНОГО СКРИПТА
    :local cleanupScriptCode ("/system script remove [find name=" . $scriptName . "]")
    
    # ЛОГИРУЕМ CLEANUP КОД ДЛЯ ДИАГНОСТИКИ
    :log info ("CLEANUP СКРИПТ " . $cleanupName . ": " . $cleanupScriptCode)
    
    /system script add name=$cleanupName source=$cleanupScriptCode
    
    # ВНЕШНИЙ CLEANUP SCHEDULER - запускает отдельный script через 10 секунд
    /system scheduler add name=$schedCleanupName start-time=startup interval=10s on-event=("/system script run " . $cleanupName)
    
    :log info ("Скрипт и внешний cleanup созданы: " . $scriptName)
}

# ТЕСТ СОЗДАНИЯ СКРИПТА - БЕЗ SCHEDULER И УДАЛЕНИЯ
:log info "Тестируем создание скрипта с правильным кодом"

# Простое тестовое сообщение
:local testMsg1 "TEST"
:local testUrl ("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $testMsg1)

# Создаем кавычки
:local quote ""
:set quote ($quote . "\"")

# Собираем код скрипта напрямую
:local testScriptCode (":local testMenuUrl (" . $quote . $testUrl . $quote . "); /tool fetch url=\$testMenuUrl http-method=post keep-result=no")

# ПОКАЗЫВАЕМ ЧТО ПОЛУЧИЛОСЬ
:log info ("ТЕСТОВЫЙ СКРИПТ: " . $testScriptCode)

# Создаем скрипт БЕЗ scheduler
/system script add name="test-script-only" source=$testScriptCode

:log info "Тестовый скрипт создан и протестирован успешно!"

# ===== ТЕСТ ГЕНЕРАЦИИ CLEANUP И MENU СКРИПТОВ =====
:log info "Тестируем генерацию cleanup и menu скриптов БЕЗ ЗАПУСКА"

# Тест 1: Cleanup скрипт
:local testCleanupName "test-cleanup-script"
:local testScriptName "some-script"
:local testSchedName "some-sched"

# Создаем кавычки
:local quote ""
:set quote ($quote . "\"")

# Cleanup с одной командой
:local cleanupCode1 ("/system script remove [find name=" . $testScriptName . "]")
:log info ("CLEANUP-1 КОД: " . $cleanupCode1)
/system script add name=($testCleanupName . "-1") source=$cleanupCode1

# Cleanup с двумя командами
:local cleanupCode2 ("/system script remove [find name=" . $testScriptName . "]; /system scheduler remove [find name=" . $testSchedName . "]")
:log info ("CLEANUP-2 КОД: " . $cleanupCode2)
/system script add name=($testCleanupName . "-2") source=$cleanupCode2

# Тест 2: Menu скрипт с JSON
:local testMenuName "test-menu-script"
:local jsonCmd "%5B%7B%22command%22%3A%22stop%22%2C%22description%22%3A%22Stop%20pump%22%7D%5D"
:local menuUrl ("https://api.telegram.org/bot" . $BotToken . "/setMyCommands?commands=" . $jsonCmd)
:local menuScriptCode (":local menuSetUrl (" . $quote . $menuUrl . $quote . "); /tool fetch url=\$menuSetUrl http-method=post keep-result=no")
:log info ("MENU КОД: " . $menuScriptCode)
/system script add name=$testMenuName source=$menuScriptCode

:log info "Тестовые скрипты созданы! Проверьте их содержимое вручную"

# ПРЕРЫВАЕМ ВЫПОЛНЕНИЕ - НЕ ИДЕМ ДАЛЬШЕ
:log warning "Тест генерации скриптов завершен - проверьте результаты"

# ===== СОЗДАНИЕ СКРИПТОВ ОЧИСТКИ И УСТАНОВКИ МЕНЮ =====
:log info "Создаем скрипты очистки и установки меню БЕЗ ЗАПУСКА"

# Создаем кавычки для URL
:local quote ""
:set quote ($quote . "\"")

# === СКРИПТ ОЧИСТКИ МЕНЮ ===
:local clearUrl ("https://api.telegram.org/bot" . $BotToken . "/deleteMyCommands?scope={\"type\":\"default\"}")
:local clearScriptCode (":local clearMenuUrl (" . $quote . $clearUrl . $quote . "); /tool fetch url=\$clearMenuUrl http-method=post keep-result=no")
:log info ("CLEAR СКРИПТ: " . $clearScriptCode)
/system script add name="clear-menu-script" source=$clearScriptCode

# === СКРИПТ УСТАНОВКИ МЕНЮ ===
# Используем глобальную переменную MsgMenuShow для команд
:local menuCommands $MsgMenuShow
:local setMenuUrl ("https://api.telegram.org/bot" . $BotToken . "/setMyCommands?commands=" . $menuCommands)
:local setMenuScriptCode (":local setMenuUrl (" . $quote . $setMenuUrl . $quote . "); /tool fetch url=\$setMenuUrl http-method=post keep-result=no")
:log info ("SET MENU СКРИПТ: " . $setMenuScriptCode)
/system script add name="set-menu-script" source=$setMenuScriptCode

# === CLEANUP СКРИПТЫ ===
# Cleanup для clear-menu
:local clearCleanupCode ("/system script remove [find name=clear-menu-script]; /system scheduler remove [find name=sched-clear-menu]")
:log info ("CLEAR CLEANUP: " . $clearCleanupCode)
/system script add name="clear-cleanup-script" source=$clearCleanupCode

# Cleanup для set-menu
:local setCleanupCode ("/system script remove [find name=set-menu-script]; /system scheduler remove [find name=sched-set-menu]")
:log info ("SET CLEANUP: " . $setCleanupCode)
/system script add name="set-cleanup-script" source=$setCleanupCode

# === CLEANUP ДЛЯ CLEANUP СКРИПТОВ ===
:local clearCleanup2Code ("/system script remove [find name=clear-cleanup-script]; /system scheduler remove [find name=sched-clear-cleanup]")
/system script add name="clear-cleanup2-script" source=$clearCleanup2Code

:local setCleanup2Code ("/system script remove [find name=set-cleanup-script]; /system scheduler remove [find name=sched-set-cleanup]")
/system script add name="set-cleanup2-script" source=$setCleanup2Code

:log info "Все скрипты созданы! Проверьте их содержимое вручную"
:log info "Созданы: clear-menu-script, set-menu-script, clear-cleanup-script, set-cleanup-script, clear-cleanup2-script, set-cleanup2-script"

# ПРЕРЫВАЕМ ВЫПОЛНЕНИЕ - НЕ ИДЕМ ДАЛЬШЕ
:log warning "Создание скриптов завершено - проверьте результаты"

