:log info "BOLER-MESSAGES: Загрузка модуля сообщений";
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
"PUMP_UNKNOWN"="Состояние насоса неизвестно";
}
:log info "BOLER-MESSAGES: Коды состояний загружены";
:global BolerLogInfo do={
:local message $1;
:local module $2;
:if ([:len $module] = 0) do={ :set module "BOLER" }
:log info "$module: $message";
}
:global BolerLogWarning do={
:local message $1;
:local module $2;
:if ([:len $module] = 0) do={ :set module "BOLER" }
:log warning "$module: $message";
}
:global BolerLogError do={
:local message $1;
:local module $2;
:if ([:len $module] = 0) do={ :set module "BOLER" }
:log error "$module: $message";
}
:global BolerLogCritical do={
:local message $1;
:local module $2;
:if ([:len $module] = 0) do={ :set module "BOLER" }
:log error "$module: КРИТИЧНО! $message";
}
:log info "BOLER-MESSAGES: Функции логирования загружены";
:global BolerMessagesLoaded true;
:global BolerLogInfo;
$BolerLogInfo "Модуль сообщений загружен successfully" "BOLER-MESSAGES";
:log info "BOLER-MESSAGES: Доступные функции:";
:log info "BOLER-MESSAGES: - BolerLogInfo, BolerLogWarning, BolerLogError, BolerLogCritical";
:log info "BOLER-MESSAGES: - BolerStatusCodes (коды состояний)";
