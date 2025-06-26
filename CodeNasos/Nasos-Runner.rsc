:global NasosInitStatus; :global BotToken; :global ChatId; :global PoeMainInterface; :global NewDuration;
:global PoeActiveTimer; :global PoeStartTime; :global PoeTimerName; :global LastStopTime; :global LastWorkDuration; :global ExpectedStopTime;
:global TestPoeStatus; :global testPoeControl; :global safePoeStatus;
:global MsgSysStarted; :global MsgSysError; :global MsgPumpOn; :global MsgPumpAlreadyOn; :global MsgPumpAutoStop; :global MsgPumpStoppedByCmd; :global MsgPumpStoppedTimeReduced;
:global MsgTimeWorked; :global MsgTimeMin; :global MsgTimeSec; :global MsgTimeReduced; :global MsgTimeWorkedTemplate; :global MsgTimeAlreadyWorkedTemplate; :global MsgTimeAlreadyWorkedTranslit;
:global MsgNewLine; :global MsgHeader; :global MsgStatusHeader; :global MsgStatusCurrent; :global MsgTimeRemaining; :global MsgTimeExpectedTotal; :global MsgTimeWorkedHeader; :global MsgTimeStoppedAt;
:global MsgPumpStartedFor; :global MsgStopCmdTemplate; :global MsgPumpAlreadyStopped; :global MsgTimeSinceStop; :global MsgErrorNoActiveTimer; :global MsgPumpUnavailable; :global MsgTestModeHeader;
:global InputSeconds; :global FormattedLog; :global FormattedTelegram;
:global TgAction; :global TgMessage; :global TgCleanupTime;
:global testPoeControl do={
:local interfaceName $1;
:local targetStatus $2;
:if ($interfaceName != "TEST") do={
:log error ("Насос - testPoeControl работает только в режиме TEST, получен: " . $interfaceName);
:return false;
}
:global TestPoeStatus;
:set TestPoeStatus $targetStatus;
:log info ("Насос - Тестовый режим: POE статус изменен на " . $targetStatus);
:return true;
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
:if ([:typeof $NasosInitStatus] = "nothing" || !$NasosInitStatus) do={
:log warning "Насос - Запуск Nasos-Init";
/system script run Nasos-Init;
}
:if ([:len $BotToken] = 0 or [:len $ChatId] = 0 or [:len $PoeMainInterface] = 0) do={
:log error "Насос - КРИТИЧЕСКАЯ ОШИБКА: Обязательные глобальные переменные не определены!";
}
:local testModePrefix "";
:if ($PoeMainInterface = "TEST") do={
:set testModePrefix ($MsgTestModeHeader . $MsgNewLine);
}
:local interfaceAvailable true;
:if ($PoeMainInterface != "TEST") do={
:if ([:len [/interface ethernet find name=$PoeMainInterface]] = 0) do={
:set interfaceAvailable false;
:log error "Насос - POE интерфейс не найден";
:global TgAction "send";
:global TgMessage $MsgPumpUnavailable;
/system script run Nasos-TG-Activator;
}
} else={
:log info "Насос - Тестовый режим активирован";
}
:if ($interfaceAvailable) do={
:local currentPoeStatus [$safePoeStatus $PoeMainInterface "off"];
:if ([:len $NewDuration] = 0) do={
:log info "Насос - Длительность не установлена";
} else={
:if ([:typeof $NewDuration] = "num") do={
:local poeStatus [$safePoeStatus $PoeMainInterface "off"];
:if ($poeStatus = "unavailable") do={
:log error "Насос - Интерфейс недоступен, команда отменена";
:global TgAction "send";
:global TgMessage $MsgPumpUnavailable;
/system script run Nasos-TG-Activator;
:set NewDuration "";
:return false;
}
:if ($NewDuration = 0) do={
:if ($poeStatus != "off") do={
:if ($PoeMainInterface = "TEST") do={
$testPoeControl $PoeMainInterface "off";
:log warning "Насос - POE ЭМУЛИРОВАННО ОТКЛЮЧЕН (тестовый режим)";
} else={
/interface ethernet poe set $PoeMainInterface poe-out=off;
:log warning "Насос - POE ФИЗИЧЕСКИ ОТКЛЮЧЕН";
}
:local workTimeMsg "";
:if ([:len $PoeStartTime] > 0) do={
:local currentTime [/system clock get time];
:local startSeconds [$timeToSeconds $PoeStartTime];
:local currentSeconds [$timeToSeconds $currentTime];
:local workSeconds ($currentSeconds - $startSeconds);
:if ($workSeconds < 0) do={
:set workSeconds ($workSeconds + 86400);
}
:set InputSeconds $workSeconds;
/system script run Nasos-TimeUtils;
:set workTimeMsg (" " . $FormattedLog);
}
:set LastStopTime [/system clock get time];
:local logMsg "Насос - НАСОС ОСТАНОВЛЕН ПО КОМАНДЕ";
:set logMsg ($logMsg . $workTimeMsg);
:log warning $logMsg;
:local telegramWorkMsg "";
:if ([:len $PoeStartTime] > 0) do={
:local currentTime [/system clock get time];
:local startSeconds [$timeToSeconds $PoeStartTime];
:local currentSeconds [$timeToSeconds $currentTime];
:local workSeconds ($currentSeconds - $startSeconds);
:if ($workSeconds < 0) do={
:set workSeconds ($workSeconds + 86400);
}
:set InputSeconds $workSeconds;
/system script run Nasos-TimeUtils;
:set telegramWorkMsg ($MsgTimeWorkedHeader . " " . $FormattedTelegram);
:set LastWorkDuration $workSeconds;
}
:local stopTime [/system clock get time];
:local telegramMsg ($testModePrefix . $MsgStatusHeader . " " . $MsgPumpStoppedByCmd . $MsgNewLine . $telegramWorkMsg . $MsgNewLine . $MsgTimeStoppedAt . $stopTime);
:global TgAction "send";
:global TgMessage $telegramMsg;
/system script run Nasos-TG-Activator;
:if ([:len $PoeActiveTimer] > 0) do={
:if ([:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
/system scheduler remove [find name=$PoeActiveTimer];
:log warning ("Насос - Удален активный таймер: " . $PoeActiveTimer);
}
:set PoeActiveTimer "";
}
:if ([:len [/system scheduler find name=$PoeTimerName]] > 0) do={
/system scheduler remove [find name=$PoeTimerName];
:log warning ("Насос - Принудительно удален таймер: " . $PoeTimerName);
}
:set PoeStartTime "";
:set ExpectedStopTime "";
:set NewDuration "";
} else={
:local timeSinceStopMsg "";
:if ([:len $LastStopTime] > 0) do={
:local currentTime [/system clock get time];
:local stopSeconds [$timeToSeconds $LastStopTime];
:local currentSeconds [$timeToSeconds $currentTime];
:local timeSinceStop ($currentSeconds - $stopSeconds);
:if ($timeSinceStop < 0) do={
:set timeSinceStop ($timeSinceStop + 86400);
}
:set InputSeconds $timeSinceStop;
/system script run Nasos-TimeUtils;
:set timeSinceStopMsg ($MsgTimeSinceStop . " " . $FormattedTelegram);
}
:log warning ("Насос - НАСОС УЖЕ ОТКЛЮЧЕН" . $timeSinceStopMsg);
:local telegramMsg ($testModePrefix . $MsgStatusHeader . " " . $MsgPumpAlreadyStopped . $MsgNewLine . $timeSinceStopMsg);
:global TgAction "send";
:global TgMessage $telegramMsg;
/system script run Nasos-TG-Activator;
:set NewDuration "";
}
} else={
:if ($NewDuration < 0) do={
:if ([:len $PoeActiveTimer] > 0) do={
:local workSeconds 0;
:local remainingSeconds 0;
:local currentTime [/system clock get time];
:local currentSeconds [$timeToSeconds $currentTime];
:if ([:len $PoeStartTime] > 0) do={
:local startSeconds [$timeToSeconds $PoeStartTime];
:set workSeconds ($currentSeconds - $startSeconds);
:if ($workSeconds < 0) do={
:set workSeconds ($workSeconds + 86400);
}
}
:if ([:len $ExpectedStopTime] > 0) do={
:local stopSeconds [$timeToSeconds $ExpectedStopTime];
:set remainingSeconds ($stopSeconds - $currentSeconds);
:if ($remainingSeconds < 0) do={
:set remainingSeconds ($remainingSeconds + 86400);
}
}
:local newRemainingSeconds ($remainingSeconds + $NewDuration);
:if ($newRemainingSeconds <= 0) do={
:local workTimeMsg "";
:if ([:len $PoeStartTime] > 0) do={
:local currentTime [/system clock get time];
:local startSeconds [$timeToSeconds $PoeStartTime];
:local currentSeconds [$timeToSeconds $currentTime];
:local workSeconds ($currentSeconds - $startSeconds);
:if ($workSeconds < 0) do={
:set workSeconds ($workSeconds + 86400);
}
:set InputSeconds $workSeconds;
/system script run Nasos-TimeUtils;
:set workTimeMsg ($MsgTimeWorkedTemplate . $FormattedTelegram);
}
:global TgAction "send";
:global TgMessage ($MsgStatusCurrent . $MsgNewLine . $MsgPumpAutoStop . $workTimeMsg);
/system script run Nasos-TG-Activator;
:set LastStopTime [/system clock get time];
:set LastWorkDuration $workSeconds;
:local logMsg "Насос - НАСОС ОСТАНОВЛЕН - время уменьшено";
:set logMsg ($logMsg . $workTimeMsg);
:log warning $logMsg;
:local telegramWorkMsg "";
:if ([:len $PoeStartTime] > 0) do={
:set InputSeconds $workSeconds;
/system script run Nasos-TimeUtils;
:set telegramWorkMsg ($MsgTimeWorkedHeader . " " . $FormattedTelegram);
}
:local telegramMsg ($testModePrefix . $MsgStatusHeader . " " . $MsgPumpStoppedTimeReduced . $MsgNewLine . $telegramWorkMsg);
:global TgAction "send";
:global TgMessage $telegramMsg;
/system script run Nasos-TG-Activator;
:if ([:len $PoeActiveTimer] > 0) do={
:if ([:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
/system scheduler remove [find name=$PoeActiveTimer];
:log warning ("Насос - Удален старый таймер: " . $PoeActiveTimer);
}
}
:if ([:len [/system scheduler find name=$PoeTimerName]] > 0) do={
/system scheduler remove [find name=$PoeTimerName];
:log warning ("Насос - Принудительно удален таймер: " . $PoeTimerName);
}
:set PoeActiveTimer "";
:set PoeStartTime "";
:set ExpectedStopTime "";
:set NewDuration "";
} else={
:local newTotalSeconds ($workSeconds + $newRemainingSeconds);
:local newIntervalHours ($newRemainingSeconds / 3600);
:local newIntervalMins (($newRemainingSeconds - ($newIntervalHours * 3600)) / 60);
:local newIntervalSecsRem ($newRemainingSeconds - ($newIntervalHours * 3600) - ($newIntervalMins * 60));
:if ($newIntervalHours < 10) do={ :set newIntervalHours ("0" . $newIntervalHours) }
:if ($newIntervalMins < 10) do={ :set newIntervalMins ("0" . $newIntervalMins) }
:if ($newIntervalSecsRem < 10) do={ :set newIntervalSecsRem ("0" . $newIntervalSecsRem) }
:local newInterval ($newIntervalHours . ":" . $newIntervalMins . ":" . $newIntervalSecsRem);
/system scheduler set [find name=$PoeActiveTimer] interval=$newInterval;
:local currentTime [/system clock get time];
:local currentSeconds [$timeToSeconds $currentTime];
:local newStopSeconds (($currentSeconds + $newRemainingSeconds) % 86400);
:local stopHours ($newStopSeconds / 3600);
:local stopMins (($newStopSeconds - ($stopHours * 3600)) / 60);
:local stopSecsRem ($newStopSeconds - ($stopHours * 3600) - ($stopMins * 60));
:if ($stopHours < 10) do={ :set stopHours ("0" . $stopHours) }
:if ($stopMins < 10) do={ :set stopMins ("0" . $stopMins) }
:if ($stopSecsRem < 10) do={ :set stopSecsRem ("0" . $stopSecsRem) }
:set ExpectedStopTime ($stopHours . ":" . $stopMins . ":" . $stopSecsRem);
:local reducedSecs (0 - $NewDuration);
:set InputSeconds $reducedSecs;
/system script run Nasos-TimeUtils;
:local reducedTimeFormatted $FormattedTelegram;
:set InputSeconds $workSeconds;
/system script run Nasos-TimeUtils;
:local workTimeFormatted $FormattedTelegram;
:set InputSeconds $newTotalSeconds;
/system script run Nasos-TimeUtils;
:local totalTimeFormatted $FormattedTelegram;
:log warning ($MsgTimeReduced . " " . $reducedTimeFormatted);
:log warning ($MsgTimeExpectedTotal . " " . $totalTimeFormatted);
:local telegramMsg ($testModePrefix . $MsgTimeReduced . " " . $reducedTimeFormatted . $MsgNewLine . $MsgTimeWorkedHeader . " " . $workTimeFormatted . $MsgNewLine . $MsgNewLine . $MsgTimeExpectedTotal . " " . $totalTimeFormatted);
:global TgAction "send";
:global TgMessage $telegramMsg;
/system script run Nasos-TG-Activator;
:set NewDuration "";
}
} else={
:log error "Насос - Нет активного таймера";
:global TgAction "send";
:global TgMessage ($MsgSysError . $MsgErrorNoActiveTimer);
/system script run Nasos-TG-Activator;
:set NewDuration "";
}
} else={
:if ($NewDuration > 0) do={
:local durationMinutes ($NewDuration / 60);
:local durationSeconds ($NewDuration - ($durationMinutes * 60));
:set InputSeconds $NewDuration;
/system script run Nasos-TimeUtils;
:local durationFormatted $FormattedTelegram;
:if ($poeStatus = "forced-on") do={
:local workTimeMsg "";
:local workSeconds 0;
:if ([:len $PoeStartTime] > 0) do={
:local currentTime [/system clock get time];
:local startSeconds [$timeToSeconds $PoeStartTime];
:local currentSeconds [$timeToSeconds $currentTime];
:set workSeconds ($currentSeconds - $startSeconds);
:if ($workSeconds < 0) do={
:set workSeconds ($workSeconds + 86400);
}
:local workMinutes ($workSeconds / 60);
:local workSecondsRem ($workSeconds - ($workMinutes * 60));
:set workTimeMsg ($MsgTimeAlreadyWorkedTemplate . [:tostr $workMinutes] . $MsgTimeMin . [:tostr $workSecondsRem] . $MsgTimeSec);
}
:local logMsg ("Насос - НАСОС УЖЕ РАБОТАЕТ - будет работать еще" . " " . $durationMinutes . " минут " . $durationSeconds . " секунд");
:set logMsg ($logMsg . $workTimeMsg);
:log warning $logMsg;
:local totalExpectedTime ($workSeconds + $NewDuration);
:local totalExpectedMinutes ($totalExpectedTime / 60);
:local totalExpectedSeconds ($totalExpectedTime - ($totalExpectedMinutes * 60));
:log warning ($MsgTimeExpectedTotal . " " . $totalExpectedMinutes . $MsgTimeMin . $totalExpectedSeconds . $MsgTimeSec);
:set InputSeconds $workSeconds;
/system script run Nasos-TimeUtils;
:local telegramWorkMsg ($MsgTimeWorkedHeader . " " . $FormattedTelegram);
:set InputSeconds $totalExpectedTime;
/system script run Nasos-TimeUtils;
:local telegramTotalMsg ($MsgTimeExpectedTotal . " " . $FormattedTelegram);
:local telegramMsg ($testModePrefix . $MsgStatusHeader . " " . $MsgPumpAlreadyOn . $MsgNewLine . $MsgTimeRemaining . " " . $durationFormatted . $MsgNewLine . $telegramWorkMsg . $MsgNewLine . $telegramTotalMsg);
:global TgAction "send";
:global TgMessage $telegramMsg;
/system script run Nasos-TG-Activator;
:local intervalHours ($NewDuration / 3600);
:local intervalMins (($NewDuration - ($intervalHours * 3600)) / 60);
:local intervalSecs ($NewDuration - ($intervalHours * 3600) - ($intervalMins * 60));
:if ($intervalHours < 10) do={ :set intervalHours ("0" . $intervalHours) }
:if ($intervalMins < 10) do={ :set intervalMins ("0" . $intervalMins) }
:if ($intervalSecs < 10) do={ :set intervalSecs ("0" . $intervalSecs) }
:local newInterval ($intervalHours . ":" . $intervalMins . ":" . $intervalSecs);
:if ([:len $PoeActiveTimer] > 0) do={
:if ([:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
/system scheduler remove [find name=$PoeActiveTimer];
:log warning ("Насос - Удален старый таймер: " . $PoeActiveTimer);
}
}
:if ([:len [/system scheduler find name=$PoeTimerName]] > 0) do={
/system scheduler remove [find name=$PoeTimerName];
:log warning ("Насос - Принудительно удален таймер: " . $PoeTimerName);
}
:local currentTime [/system clock get time];
:local currentSeconds [$timeToSeconds $currentTime];
:local stopSeconds (($currentSeconds + $NewDuration) % 86400);
:local stopHours ($stopSeconds / 3600);
:local stopMins (($stopSeconds - ($stopHours * 3600)) / 60);
:local stopSecsRem ($stopSeconds - ($stopHours * 3600) - ($stopMins * 60));
:if ($stopHours < 10) do={ :set stopHours ("0" . $stopHours) }
:if ($stopMins < 10) do={ :set stopMins ("0" . $stopMins) }
:if ($stopSecsRem < 10) do={ :set stopSecsRem ("0" . $stopSecsRem) }
:set ExpectedStopTime ($stopHours . ":" . $stopMins . ":" . $stopSecsRem);
:local timerName $PoeTimerName;
/system scheduler add name=$timerName interval=$newInterval on-event=$MsgStopCmdTemplate;
:set PoeActiveTimer $timerName;
:log warning ("Насос - Создан новый таймер: " . $timerName . " с интервалом: " . $newInterval . ", ожидаемая остановка: " . $ExpectedStopTime);
} else={
:if ($PoeMainInterface = "TEST") do={
$testPoeControl $PoeMainInterface "forced-on";
:log warning "Насос - POE ЭМУЛИРОВАННО ВКЛЮЧЕН (тестовый режим)";
} else={
/interface ethernet set [find name=$PoeMainInterface] poe-out=forced-on;
:log warning "Насос - POE ФИЗИЧЕСКИ ВКЛЮЧЕН";
}
:set PoeStartTime [/system clock get time];
:local logMsg ("Насос - НАСОС ЗАПУЩЕН на " . $durationMinutes . " минут " . $durationSeconds . " секунд");
:log warning $logMsg;
:local telegramMsg ($testModePrefix . $MsgStatusHeader . " " . $MsgPumpOn . $MsgNewLine . $MsgPumpStartedFor . " " . $durationFormatted);
:global TgAction "send";
:global TgMessage $telegramMsg;
/system script run Nasos-TG-Activator;
:local intervalHours ($NewDuration / 3600);
:local intervalMins (($NewDuration - ($intervalHours * 3600)) / 60);
:local intervalSecs ($NewDuration - ($intervalHours * 3600) - ($intervalMins * 60));
:if ($intervalHours < 10) do={ :set intervalHours ("0" . $intervalHours) }
:if ($intervalMins < 10) do={ :set intervalMins ("0" . $intervalMins) }
:if ($intervalSecs < 10) do={ :set intervalSecs ("0" . $intervalSecs) }
:local schedulerInterval ($intervalHours . ":" . $intervalMins . ":" . $intervalSecs);
:if ([:len $PoeActiveTimer] > 0) do={
:if ([:len [/system scheduler find name=$PoeActiveTimer]] > 0) do={
/system scheduler remove [find name=$PoeActiveTimer];
:log warning ("Насос - Удален старый таймер: " . $PoeActiveTimer);
}
}
:if ([:len [/system scheduler find name=$PoeTimerName]] > 0) do={
/system scheduler remove [find name=$PoeTimerName];
:log warning ("Насос - Принудительно удален таймер: " . $PoeTimerName);
}
:local currentTime [/system clock get time];
:local currentSeconds [$timeToSeconds $currentTime];
:local stopSeconds (($currentSeconds + $NewDuration) % 86400);
:local stopHours ($stopSeconds / 3600);
:local stopMins (($stopSeconds - ($stopHours * 3600)) / 60);
:local stopSecsRem ($stopSeconds - ($stopHours * 3600) - ($stopMins * 60));
:if ($stopHours < 10) do={ :set stopHours ("0" . $stopHours) }
:if ($stopMins < 10) do={ :set stopMins ("0" . $stopMins) }
:if ($stopSecsRem < 10) do={ :set stopSecsRem ("0" . $stopSecsRem) }
:set ExpectedStopTime ($stopHours . ":" . $stopMins . ":" . $stopSecsRem);
:local timerName $PoeTimerName;
/system scheduler add name=$timerName interval=$schedulerInterval on-event=$MsgStopCmdTemplate;
:set PoeActiveTimer $timerName;
:log warning ("Насос - Создан новый таймер: " . $timerName . " с интервалом: " . $schedulerInterval . ", ожидаемая остановка: " . $ExpectedStopTime);
}
:set NewDuration "";
}
}
}
} else={
:log error "Насос - Длительность должна быть числом";
}
}
}
