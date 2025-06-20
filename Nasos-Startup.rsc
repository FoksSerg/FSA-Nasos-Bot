# ===== NASOS STARTUP =====
# Модуль автоматического запуска системы управления насосом при загрузке роутера
# Автор: Фокин Сергей Александрович foks_serg@mail.ru
# Дата создания: 15 июня 2025
# Версия: 1.4

:log info "Насос - Конфигурация автоматического запуска..."

# Объявление глобальных переменных
:global NasosInitStatus
:global BotToken
:global ChatId
:global MsgSysReboot

# Инициализация модуля сообщений
:log warning "Насос - Запуск Nasos-Messages"
/system script run Nasos-Messages

# Проверка инициализации основных переменных
:if ([:typeof $NasosInitStatus] = "nothing" || !$NasosInitStatus) do={
    :log warning "Насос - Запуск Nasos-Init"
    /system script run Nasos-Init
}

# Очистка старых таймеров автозапуска
:if ([:len [/system scheduler find name="nasos-telegram-startup"]] > 0) do={
    /system scheduler remove [find name="nasos-telegram-startup"]
    :log info "Насос - Удален старый загрузчик Телеграм"
}
:if ([:len [/system scheduler find name="nasos-watchdog-timer"]] > 0) do={
    /system scheduler remove [find name="nasos-watchdog-timer"]
    :log info "Насос - Удален старый сторожевой таймер"
}

# Пауза для завершения инициализации
:delay 2s
:log info "Насос - Глобальные переменные инициализированы"

# Создание таймера автозапуска Telegram модуля
/system scheduler add name="nasos-telegram-startup" start-time=startup start-date=jan/01/1970 interval=0 on-event=":delay 1m; /system script run Nasos-Telegram"
:log info "Насос - Создан стартовый загрузчик Телеграм (1 минута после загрузки)"

# Создание сторожевого таймера для мониторинга
/system scheduler add name="nasos-watchdog-timer" start-time=startup start-date=jan/01/1970 interval=5m on-event=":delay 1m30s; /system script run Nasos-WatchDog"
:log info "Насос - Создан сторожевой таймер (5 минут интервал)"

# Отправка уведомления о перезагрузке системы
:local startupMsg "NASOS SYSTEM: Router rebooted, services configured"
/tool fetch url=("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $startupMsg) keep-result=no
:log info "Насос - Конфигурация выполнена!" 