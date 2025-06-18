:global TelegramSendStatus
:global TelegramSendError
:global TelegramSendMsg

:log warning "==== Start Test ===="

# Функция для вычисления времени +1 секунда
:global nextTime do={
    :local now [/system clock get time]
    :local hour [:tonum [:pick $now 0 2]]
    :local min [:tonum [:pick $now 3 5]]
    :local sec ([:tonum [:pick $now 6 8]] + 1)
    :if ($sec > 59) do={
        :set sec 0
        :set min ($min + 1)
        :if ($min > 59) do={
            :set min 0
            :set hour ($hour + 1)
            :if ($hour > 23) do={ :set hour 0 }
        }
    }
    :return ([:tostr $hour] . ":" . [:tostr $min] . ":" . [:tostr $sec])
}

:set TelegramSendMsg "TEST-1"
:set TelegramSendStatus ""
:set TelegramSendError ""
:local t1 [$nextTime]
/system scheduler add name="send-tg-1" interval=0 start-time=$t1 on-event="/system script run Send-Telegram"
:delay 3s
:log info ("[Test] TelegramSendStatus=" . $TelegramSendStatus . ", TelegramSendError=" . $TelegramSendError)

:set TelegramSendMsg "TEST-2"
:set TelegramSendStatus ""
:set TelegramSendError ""
:local t2 [$nextTime]
/system scheduler add name="send-tg-2" interval=0 start-time=$t2 on-event="/system script run Send-Telegram"
:delay 3s
:log info ("[Test] TelegramSendStatus=" . $TelegramSendStatus . ", TelegramSendError=" . $TelegramSendError)

:set TelegramSendMsg "TEST-3"
:set TelegramSendStatus ""
:set TelegramSendError ""
:local t3 [$nextTime]
/system scheduler add name="send-tg-3" interval=0 start-time=$t3 on-event="/system script run Send-Telegram"
:delay 3s
:log info ("[Test] TelegramSendStatus=" . $TelegramSendStatus . ", TelegramSendError=" . $TelegramSendError)

/system scheduler remove [find name="send-tg-1"]
/system scheduler remove [find name="send-tg-2"]
/system scheduler remove [find name="send-tg-3"]

:log warning "Test fetch завершён"