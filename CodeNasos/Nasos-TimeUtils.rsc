:global formatTimeInterval; :global calculateTimeDiff; :global InputSeconds; :global FormattedLog; :global FormattedTelegram;
:global formatTimeInterval do={
:local totalSeconds $1;
:local dayShort " дн.";
:local hourShort " час.";
:local minShort " мин.";
:local secShort " сек.";
:local dayShortTg "%20%D0%B4%D0%BD%2E%20";
:local hourShortTg "%20%D1%87%D0%B0%D1%81%2E%20";
:local minShortTg "%20%D0%BC%D0%B8%D0%BD%2E%20";
:local secShortTg "%20%D1%81%D0%B5%D0%BA%2E";
:if ($totalSeconds <= 0) do={
:global FormattedLog "0 сек.";
:global FormattedTelegram "0%20%D1%81%D0%B5%D0%BA%2E";
:return;
}
:local days ($totalSeconds / 86400);
:local remainingAfterDays ($totalSeconds - ($days * 86400));
:local hours ($remainingAfterDays / 3600);
:local remainingAfterHours ($remainingAfterDays - ($hours * 3600));
:local minutes ($remainingAfterHours / 60);
:local seconds ($remainingAfterHours - ($minutes * 60));
:local resultLog "";
:if ($days > 0) do={ :set resultLog ($resultLog . $days . $dayShort) }
:if ($hours > 0) do={ :set resultLog ($resultLog . $hours . $hourShort) }
:if ($minutes > 0) do={ :set resultLog ($resultLog . $minutes . $minShort) }
:if ($seconds > 0) do={ :set resultLog ($resultLog . $seconds . $secShort) }
:local resultTg "";
:if ($days > 0) do={ :set resultTg ($resultTg . $days . $dayShortTg) }
:if ($hours > 0) do={ :set resultTg ($resultTg . $hours . $hourShortTg) }
:if ($minutes > 0) do={ :set resultTg ($resultTg . $minutes . $minShortTg) }
:if ($seconds > 0) do={ :set resultTg ($resultTg . $seconds . $secShortTg) }
:if ([:len $resultLog] = 0) do={
:set resultLog "0 сек.";
:set resultTg "0%20%D1%81%D0%B5%D0%BA%2E";
}
:global FormattedLog $resultLog;
:global FormattedTelegram $resultTg;
}
:if ([:typeof $InputSeconds] != "nothing") do={
[$formatTimeInterval $InputSeconds];
}
:global calculateTimeDiff do={
:local startTime $1;
:local currentTime $2;
:local startHours [:pick $startTime 0 2];
:local startMinutes [:pick $startTime 3 5];
:local startSecs [:pick $startTime 6 8];
:local startSeconds ($startHours * 3600 + $startMinutes * 60 + $startSecs);
:local currentHours [:pick $currentTime 0 2];
:local currentMins [:pick $currentTime 3 5];
:local currentSecs [:pick $currentTime 6 8];
:local currentSeconds ($currentHours * 3600 + $currentMins * 60 + $currentSecs);
:local diff ($currentSeconds - $startSeconds);
:if ($diff < 0) do={
:set diff ($diff + 86400);
}
:return $diff;
}
