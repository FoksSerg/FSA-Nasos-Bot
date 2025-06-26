:global NasosInitStatus;
:global BotToken;
:global ChatId;
:global TelegramHeartbeat;
:global MsgNewLine;
:global MsgSysWatchdogTimeout;
:global MsgSysWatchdogMin;
:global MsgSysWatchdogRestart;
:if ([:typeof $NasosInitStatus] = "nothing" || !$NasosInitStatus) do={
:log warning "Насос - Запуск Nasos-Init";
/system script run Nasos-Init;
}
:local currentTime [/system clock get time];
:local timeoutMinutes 10;
:if ([:len $TelegramHeartbeat] > 0) do={
:local heartbeatHours [:pick $TelegramHeartbeat 0 2];
:local heartbeatMins [:pick $TelegramHeartbeat 3 5];
:local heartbeatSecs [:pick $TelegramHeartbeat 6 8];
:local heartbeatSeconds ($heartbeatHours * 3600 + $heartbeatMins * 60 + $heartbeatSecs);
:local currentHours [:pick $currentTime 0 2];
:local currentMins [:pick $currentTime 3 5];
:local currentSecs [:pick $currentTime 6 8];
:local currentSeconds ($currentHours * 3600 + $currentMins * 60 + $currentSecs);
:local timeDiff ($currentSeconds - $heartbeatSeconds);
:if ($timeDiff < 0) do={
:set timeDiff ($timeDiff + 86400);
}
:local diffMinutes ($timeDiff / 60);
:if ($diffMinutes > $timeoutMinutes) do={
:log error ("Насос - Telegram парсер не отвечает " . $diffMinutes . " минут - перезапуск");
:local alertMsg ($MsgSysWatchdogTimeout . $diffMinutes . $MsgTimeMin);
/tool fetch url=("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $alertMsg) keep-result=no;
:if ([:len [/system script job find script="Nasos-Telegram"]] > 0) do={
/system script job remove [find script="Nasos-Telegram"];
:log warning "Насос - Завершен существующий процесс Nasos-Telegram";
}
:delay 2s;
/system script run Nasos-Telegram;
:log warning "Насос - Перезапущен скрипт Nasos-Telegram";
}
} else={
:log warning "Насос - Heartbeat не найден - запуск Nasos-Telegram";
/tool fetch url=("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $MsgSysWatchdogRestart) keep-result=no;
/system script run Nasos-Telegram;
}
