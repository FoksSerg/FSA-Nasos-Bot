:global NasosInitStatus; :global BotToken; :global ChatId; :global LastUpdateId; :global TelegramHeartbeat;
:global NewDuration; :global PoeMainInterface; :global PoeStartTime; :global PoeActiveTimer; :global LastStopTime; :global LastWorkDuration;
:global TestPoeStatus;
:global TgAction; :global TgMessage;
:global MsgSysStarted; :global MsgSysError; :global MsgEmergencyShutdown; :global MsgEmergencyReason; :global MsgMenuHeader; :global MsgNewLine; :global MsgHeader; :global MsgStatusHeader;
:global MsgPumpOn; :global MsgPumpOff; :global MsgStatusWorkingTime; :global MsgStatusTimeLeft; :global MsgStatusTimerExpired; :global MsgStatusNoAutoStop;
:global MsgStatusStoppedTime; :global MsgStatusTimeAgo; :global MsgTimeExpectedTotal; :global MsgStatusLastStopUnknown; :global ExpectedStopTime; :global MsgTimeWorkedHeader;
:global InputSeconds; :global FormattedTelegram;
:global testPoeControl;
:global TgLastCommand; :global TgCommandTime; :global TgPollStatus; :global TgPollError; :global TgPollHeartbeat; :global TgStartMinutes;
:global MsgMenuStop; :global MsgMenuStatus; :global MsgMenuShow; :global MsgMenuStart5; :global MsgMenuStart10; :global MsgMenuStart30; :global MsgMenuStart60; :global MsgMenuStart120;
:global timeToSeconds do={
:local timeStr $1;
:if ([:typeof $timeStr] = "nothing" || [:len $timeStr] = 0 || [:len $timeStr] < 8) do={
:return 0;
}
:local hours [:pick $timeStr 0 2];
:local minutes [:pick $timeStr 3 5];
:local seconds [:pick $timeStr 6 8];
:if ([:typeof [:tonum $hours]] = "nothing" || [:typeof [:tonum $minutes]] = "nothing" || [:typeof [:tonum $seconds]] = "nothing") do={
:return 0;
}
:return ($hours * 3600 + $minutes * 60 + $seconds);
}
:global safePoeStatus do={
:local interfaceName $1;
:local defaultStatus $2;
:if ([:typeof $interfaceName] = "nothing" || [:len $interfaceName] = 0) do={
:log error "Насос - safePoeStatus: Не указан интерфейс!";
:return $defaultStatus;
}
:if ($interfaceName = "TEST") do={
:global TestPoeStatus;
:log info ("Насос - Тестовый режим: эмулируемый статус POE = " . $TestPoeStatus);
:return $TestPoeStatus;
}
:do {
:local interfaceId [/interface ethernet find name=$interfaceName];
:if ([:len $interfaceId] = 0) do={
:log error ("Насос - Интерфейс '" . $interfaceName . "' не найден!");
:return "unavailable";
}
:local poeStatus [/interface ethernet get $interfaceId poe-out];
:return $poeStatus;
} on-error={
:log error ("Насос - Ошибка получения POE статуса для '" . $interfaceName . "'");
:return "unavailable";
}
}
:log info "Насос - Telegram v4.0: Запуск оптимизированной версии";
:local initAttempts 0;
:local maxInitAttempts 3;
:local initSuccess false;
:while (!$initSuccess && $initAttempts < $maxInitAttempts) do={
:set initAttempts ($initAttempts + 1);
:log warning ("Насос - Инициализация попытка #" . $initAttempts);
:if ([:typeof $NasosInitStatus] = "nothing" || !$NasosInitStatus) do={
:log warning "Насос - Запуск Nasos-Init";
/system script run Nasos-Init;
:delay 2s;
}
:if ([:len $BotToken] = 0 or [:len $ChatId] = 0 or [:len $PoeMainInterface] = 0) do={
:log error ("Насос - Попытка #" . $initAttempts . ": Критичные переменные не готовы");
:if ($initAttempts < $maxInitAttempts) do={
:delay 3s;
}
} else={
:set initSuccess true;
:log info "Насос - Инициализация успешна!";
}
}
:if (!$initSuccess) do={
:log error "Насос - КРИТИЧЕСКАЯ ОШИБКА: Инициализация провалена!";
:return false;
}
:if ([:typeof $LastUpdateId] = "nothing" || [:len $LastUpdateId] = 0) do={
:log info "Насос - Получение начального offset...";
:do {
:local initUpdates [/tool fetch url=("https://api.telegram.org/bot" . $BotToken . "/getUpdates?offset=-1&limit=1") as-value output=user];
:local initContent ($initUpdates->"data");
:local updateIdPos [:find $initContent "\"update_id\":"];
:if ([:len $updateIdPos] > 0) do={
:local idStart ($updateIdPos + 12);
:local idEnd [:find $initContent "," $idStart];
:local latestUpdateId [:pick $initContent $idStart $idEnd];
:set LastUpdateId ($latestUpdateId + 1);
:log info ("Насос - Offset установлен: " . $LastUpdateId);
} else={
:set LastUpdateId 1;
:log info "Насос - Offset по умолчанию: 1";
}
} on-error={
:set LastUpdateId 1;
:log warning "Насос - Ошибка получения offset, используем: 1";
}
} else={
:log info ("Насос - Продолжаем с offset: " . $LastUpdateId);
}
:log info "Насос - Отправка приветственного сообщения...";
:local poeStatus [$safePoeStatus $PoeMainInterface "off"];
:local statusMsg;
:if ($poeStatus = "forced-on") do={
:set statusMsg $MsgPumpOn;
} else={
:set statusMsg $MsgPumpOff;
}
:local welcomeMsg ($MsgSysStarted . $MsgNewLine . $statusMsg);
:set TgAction "send";
:set TgMessage $welcomeMsg;
:do {
/system script run Nasos-TG-Activator;
} on-error={
:log warning "Насос - Ошибка отправки приветствия";
}
:delay 1s;
:local loopCounter 0;
:while (true) do={
:set loopCounter ($loopCounter + 1);
:set TelegramHeartbeat [/system clock get time];
:local poeStatus [$safePoeStatus $PoeMainInterface "off"];
:if ($poeStatus = "auto-on" || $poeStatus = "forced-on") do={
:if ([:len $PoeActiveTimer] = 0 || [:len [/system scheduler find name=$PoeActiveTimer]] = 0) do={
:log error "КРИТИЧНО: Насос работает без автостопа - принудительное отключение!";
:if ($PoeMainInterface = "TEST") do={
:global testPoeControl;
$testPoeControl $PoeMainInterface "off";
} else={
/interface ethernet poe set $PoeMainInterface poe-out=off;
}
:local emergencyWorkSeconds 0;
:if ([:len $PoeStartTime] > 0) do={
:local currentTime [/system clock get time];
:local startSeconds [$timeToSeconds $PoeStartTime];
:local currentSeconds [$timeToSeconds $currentTime];
:if ($startSeconds >= 0 && $currentSeconds >= 0) do={
:set emergencyWorkSeconds ($currentSeconds - $startSeconds);
:if ($emergencyWorkSeconds < 0) do={
:set emergencyWorkSeconds ($emergencyWorkSeconds + 86400);
}
}
}
:set LastStopTime [/system clock get time];
:set LastWorkDuration $emergencyWorkSeconds;
:set PoeStartTime "";
:set ExpectedStopTime "";
:set PoeActiveTimer "";
:if ([:len [/system scheduler find name=$PoeTimerName]] > 0) do={
/system scheduler remove [find name=$PoeTimerName];
:log warning ("Насос - Принудительно удален таймер при аварийном отключении: " . $PoeTimerName);
}
:local emergencyMsg ($MsgSysError . $MsgEmergencyShutdown . $MsgNewLine . $MsgEmergencyReason);
:if ($emergencyWorkSeconds > 0) do={
:set InputSeconds $emergencyWorkSeconds;
:do {
/system script run Nasos-TimeUtils;
:set emergencyMsg ($emergencyMsg . $MsgNewLine . $MsgTimeWorkedHeader . " " . $FormattedTelegram);
} on-error={}
}
:set TgAction "send";
:set TgMessage $emergencyMsg;
:do {
/system script run Nasos-TG-Activator;
} on-error={}
}
}
:set TgAction "poll";
:do {
/system script run Nasos-TG-Activator;
} on-error={
:log warning "Насос - Ошибка запуска TG-Activator";
:set TgPollStatus "error";
:set TgPollError "Ошибка запуска активатора";
}
:delay 1s;
:if ([:len $TgLastCommand] > 0 && $TgPollStatus = "ok") do={
:if ($TgLastCommand = "start") do={
:local minutes $TgStartMinutes;
:if ([:typeof $minutes] = "nothing" || [:typeof $minutes] != "num") do={
:log warning "Ошибка: некорректное значение минут";
:set TgLastCommand "";
} else={
:if ($minutes = 0) do={
:log warning "СТОП (через start0)";
:set NewDuration 0;
} else={
:if ($minutes > 0) do={
:log warning ("СТАРТ " . $minutes . " мин");
} else={
:log warning ("УМЕНЬШЕНИЕ на " . ($minutes * -1) . " мин");
}
:set NewDuration ($minutes * 60);
}
:do {
/system script run Nasos-Runner;
} on-error={
:log warning "Ошибка запуска Runner";
}
:set TgLastCommand "";
}
}
:if ($TgLastCommand = "stop") do={
:log warning "СТОП";
:set NewDuration 0;
/system script run Nasos-Runner;
:set TgLastCommand "";
}
:if ($TgLastCommand = "status") do={
:if ([:len $LastStopTime] > 8) do={
:set LastStopTime "";
}
:local poeStatus [$safePoeStatus $PoeMainInterface "off"];
:local currentTime [/system clock get time];
:local statusText ($MsgHeader . $MsgNewLine);
:if ($poeStatus = "forced-on") do={
:set statusText ($statusText . $MsgStatusHeader . " " . $MsgPumpOn);
:local workSeconds 0;
:if ([:len $PoeStartTime] > 0) do={
:local startSeconds [$timeToSeconds $PoeStartTime];
:local currentSeconds [$timeToSeconds $currentTime];
:if ($startSeconds >= 0 && $currentSeconds >= 0) do={
:set workSeconds ($currentSeconds - $startSeconds);
:if ($workSeconds < 0) do={
:set workSeconds ($workSeconds + 86400);
}
:if ($workSeconds >= 0) do={
:set InputSeconds $workSeconds;
:do {
/system script run Nasos-TimeUtils;
:set statusText ($statusText . $MsgNewLine . $MsgStatusWorkingTime . $FormattedTelegram);
} on-error={
:set statusText ($statusText . $MsgNewLine . $MsgStatusWorkingTime . "ошибка расчета");
}
}
}
}
:if ([:len $PoeActiveTimer] > 0 && [:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
:local timerInterval [/system scheduler get [find name=$PoeActiveTimer] interval];
:local totalSeconds [$timeToSeconds $timerInterval];
:local remainingSeconds 0;
:if ([:len $ExpectedStopTime] > 0) do={
:local currentTime [/system clock get time];
:local currentSeconds [$timeToSeconds $currentTime];
:local stopSeconds [$timeToSeconds $ExpectedStopTime];
:if ($currentSeconds >= 0 && $stopSeconds >= 0) do={
:set remainingSeconds ($stopSeconds - $currentSeconds);
:if ($remainingSeconds < 0) do={
:set remainingSeconds ($remainingSeconds + 86400);
}
:if ($remainingSeconds > 86400) do={
:set remainingSeconds 0;
}
}
}
:if ($remainingSeconds > 0) do={
:set InputSeconds $remainingSeconds;
:do {
/system script run Nasos-TimeUtils;
:set statusText ($statusText . $MsgNewLine . $MsgStatusTimeLeft . $FormattedTelegram);
} on-error={
:set statusText ($statusText . $MsgNewLine . $MsgStatusTimeLeft . "ошибка расчета");
}
:local expectedTotalSeconds ($workSeconds + $remainingSeconds);
:if ($expectedTotalSeconds >= 0) do={
:set InputSeconds $expectedTotalSeconds;
:do {
/system script run Nasos-TimeUtils;
:set statusText ($statusText . $MsgNewLine . $MsgTimeExpectedTotal . " " . $FormattedTelegram);
} on-error={
:set statusText ($statusText . $MsgNewLine . $MsgTimeExpectedTotal . " ошибка расчета");
}
}
} else={
:set statusText ($statusText . $MsgNewLine . $MsgStatusTimerExpired);
}
} else={
:set statusText ($statusText . $MsgNewLine . $MsgStatusNoAutoStop);
}
} else={
:set statusText ($statusText . $MsgStatusHeader . " " . $MsgPumpOff);
:if ([:len $LastStopTime] > 0) do={
:local stopSeconds [$timeToSeconds $LastStopTime];
:local currentSeconds [$timeToSeconds $currentTime];
:if ($stopSeconds >= 0 && $currentSeconds >= 0) do={
:local stopDiffSeconds ($currentSeconds - $stopSeconds);
:if ($stopDiffSeconds < 0) do={
:set stopDiffSeconds ($stopDiffSeconds + 86400);
}
:if ($stopDiffSeconds >= 0) do={
:set InputSeconds $stopDiffSeconds;
:do {
/system script run Nasos-TimeUtils;
:set statusText ($statusText . $MsgNewLine . $MsgStatusStoppedTime . $FormattedTelegram . $MsgStatusTimeAgo);
} on-error={
:set statusText ($statusText . $MsgNewLine . $MsgStatusStoppedTime . "ошибка расчета" . $MsgStatusTimeAgo);
}
}
} else={
:set statusText ($statusText . $MsgNewLine . $MsgStatusLastStopUnknown);
}
} else={
:set statusText ($statusText . $MsgNewLine . $MsgStatusLastStopUnknown);
}
:if ([:typeof $LastWorkDuration] = "num" && $LastWorkDuration > 0) do={
:set InputSeconds $LastWorkDuration;
:do {
/system script run Nasos-TimeUtils;
:set statusText ($statusText . $MsgNewLine . $MsgTimeWorkedHeader . " " . $FormattedTelegram);
} on-error={
:set statusText ($statusText . $MsgNewLine . $MsgTimeWorkedHeader . " ошибка расчета");
}
}
}
:set TgAction "send";
:set TgMessage $statusText;
:do {
/system script run Nasos-TG-Activator;
} on-error={
:log warning "Насос - Ошибка отправки STATUS";
}
:set TgLastCommand "";
}
:if ($TgLastCommand = "menu") do={
:local menuMsg ($MsgMenuHeader . $MsgNewLine . $MsgNewLine . $MsgMenuStop . $MsgNewLine . $MsgMenuStatus . $MsgNewLine . $MsgMenuShow . $MsgNewLine . $MsgNewLine . $MsgMenuStart5 . $MsgNewLine . $MsgMenuStart10 . $MsgNewLine . $MsgMenuStart30 . $MsgNewLine . $MsgMenuStart60 . $MsgNewLine . $MsgMenuStart120);
:set TgAction "send";
:set TgMessage $menuMsg;
:do {
/system script run Nasos-TG-Activator;
} on-error={
:log warning "Насос - Ошибка отправки MENU";
}
:set TgLastCommand "";
}
} else={
:if ($TgPollStatus = "error") do={
:log warning ("Насос - Ошибка API: " . $TgPollError);
}
}
:delay 4s;
}
