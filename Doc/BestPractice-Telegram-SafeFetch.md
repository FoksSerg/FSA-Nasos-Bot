# Best Practice: Надёжная отправка HTTP/Telegram из скриптов MikroTik RouterOS (без риска аварийного завершения)

## Проблема
- В RouterOS любой fetch с ошибкой (HTTP 4xx/5xx, DNS, TLS) аварийно завершает скрипт, даже если он запущен как job или через `/system script run`.
- Это делает невозможным надёжную обработку ошибок и гарантированное завершение основного скрипта, если нужен HTTP-запрос.

---

## Решение: Использование /system scheduler для полной изоляции

### 1. Вынесите отправку fetch в отдельный скрипт (например, Send-Telegram):
```rsc
:global BotToken
:global ChatId
:global TelegramSendStatus
:global TelegramSendError
:global TelegramSendMsg

:set TelegramSendStatus "started"
:set TelegramSendError ""
:local msg $TelegramSendMsg
:local url ("https://api.telegram.org/bot" . $BotToken . "/sendMessage?chat_id=" . $ChatId . "&text=" . $msg)
/tool fetch url=$url keep-result=no
:set TelegramSendStatus "done"
:set TelegramSendError ""
```

### 2. В основном скрипте для каждой отправки:
- Вычисляйте текущее время + 1 секунда (минимальный шаг в RouterOS).
- Создавайте задачу scheduler с этим временем и нужным on-event.
- После паузы (2-3 сек) анализируйте глобальные переменные, продолжайте работу.

```rsc
:global TelegramSendStatus
:global TelegramSendError
:global TelegramSendMsg

# Функция для времени +1 сек
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

:log warning "==== Start Test ===="

:set TelegramSendMsg "TEST-1"
:set TelegramSendStatus ""
:set TelegramSendError ""
:local t1 [$nextTime]
/system scheduler add name="send-tg-1" interval=0 start-time=$t1 on-event="/system script run Send-Telegram"
:delay 3s
:log info ("[Test] TelegramSendStatus=" . $TelegramSendStatus . ", TelegramSendError=" . $TelegramSendError)

# Повторить для других сообщений...

/system scheduler remove [find name="send-tg-1"]
:log warning "Test fetch завершён"
```

---

## Преимущества
- **Основной скрипт всегда доходит до конца**, даже если fetch завершился ошибкой.
- **Ошибки fetch не влияют на логику основного процесса** — только в системном логе.
- **Можно отправлять любое количество сообщений, не опасаясь аварийных остановок.**
- **Работает на любом MikroTik, не требует внешних серверов.**

---

## Кратко:
- **Любой потенциально аварийный fetch — только через scheduler!**
- **Основной скрипт — только создание задач и анализ результата через глобальные переменные.**

---

Этот паттерн — "секретное оружие" для надёжных автоматизаций на MikroTik! 