# Система мониторинга уровня Boler - Модуль сообщений
# Название: Boler-Messages.rsc
# Версия: 1.0
# Дата: 28 июня 2025
# Автор: Фокин Сергей Александрович
# Описание: Кодированные сообщения и функции форматирования для системы Boler

:log info "BOLER-MESSAGES: Загрузка модуля сообщений"

# КОДЫ СОСТОЯНИЙ СИСТЕМЫ

:global BolerStatusCodes {
    "INIT"="Инициализация системы";
    "READY"="Система готова";
    "MONITORING"="Мониторинг активен";
    "SENSOR_ERROR"="Ошибка датчиков";
    "NETWORK_ERROR"="Ошибка сети";
    "CRITICAL_LEVEL"="Критический уровень!";
    "WORK_LEVEL"="Рабочий уровень";
    "NO_LEVEL"="Уровень не достигнут";
    "CONNECTION_LOST"="Связь с Nasos потеряна";
    "PUMP_RUNNING"="Насос работает";
    "PUMP_STOPPED"="Насос остановлен";
    "PUMP_UNKNOWN"="Состояние насоса неизвестно"
}

:log info "BOLER-MESSAGES: Коды состояний загружены"

# ФУНКЦИИ ЛОГИРОВАНИЯ С ПРЕФИКСАМИ

# Функция логирования информационных сообщений
:global BolerLogInfo do={
    :local message $1
    :local module $2
    
    :if ([:len $module] = 0) do={ :set module "BOLER" }
    :log info "$module: $message"
}

# Функция логирования предупреждений
:global BolerLogWarning do={
    :local message $1
    :local module $2
    
    :if ([:len $module] = 0) do={ :set module "BOLER" }
    :log warning "$module: $message"
}

# Функция логирования ошибок
:global BolerLogError do={
    :local message $1
    :local module $2
    
    :if ([:len $module] = 0) do={ :set module "BOLER" }
    :log error "$module: $message"
}

# Функция логирования критических сообщений
:global BolerLogCritical do={
    :local message $1
    :local module $2
    
    :if ([:len $module] = 0) do={ :set module "BOLER" }
    :log error "$module: КРИТИЧНО! $message"
}

:log info "BOLER-MESSAGES: Функции логирования загружены"

# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ

# Устанавливаем флаг загрузки модуля сообщений
:global BolerMessagesLoaded true

:global BolerLogInfo
$BolerLogInfo "Модуль сообщений загружен successfully" "BOLER-MESSAGES"

# Показываем доступные функции
:log info "BOLER-MESSAGES: Доступные функции:"
:log info "BOLER-MESSAGES: - BolerLogInfo, BolerLogWarning, BolerLogError, BolerLogCritical"
:log info "BOLER-MESSAGES: - BolerStatusCodes (коды состояний)" 