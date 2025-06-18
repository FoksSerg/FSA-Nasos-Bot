# ===== NASOS TELEGRAM BOT MESSAGES =====

# ===== 1. СИСТЕМНЫЕ СООБЩЕНИЯ =====
# Форматирование
:global MsgNewLine "%0A"

# Заголовок системы
# 🚰 СИСТЕМА УПРАВЛЕНИЯ НАСОСОМ 💧
:global MsgHeader "%F0%9F%9A%B0%20%D0%A1%D0%98%D0%A1%D0%A2%D0%95%D0%9C%D0%90%20%D0%A3%D0%9F%D0%A0%D0%90%D0%92%D0%9B%D0%95%D0%9D%D0%98%D0%AF%20%D0%9D%D0%90%D0%A1%D0%9E%D0%A1%D0%9E%D0%9C%20%F0%9F%92%A7"

# Системные статусы
# 🚰 СИСТЕМА УПРАВЛЕНИЯ НАСОСОМ 💧 / ✅ Бот запущен и готов к работе
:global MsgSysStarted "%F0%9F%9A%B0%20%D0%A1%D0%98%D0%A1%D0%A2%D0%95%D0%9C%D0%90%20%D0%A3%D0%9F%D0%A0%D0%90%D0%92%D0%9B%D0%95%D0%9D%D0%98%D0%AF%20%D0%9D%D0%90%D0%A1%D0%9E%D0%A1%D0%9E%D0%9C%20%F0%9F%92%A7%0A%E2%9C%85%20%D0%91%D0%BE%D1%82%20%D0%B7%D0%B0%D0%BF%D1%83%D1%89%D0%B5%D0%BD%20%D0%B8%20%D0%B3%D0%BE%D1%82%D0%BE%D0%B2%20%D0%BA%20%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B5"
# 🚰 СИСТЕМА УПРАВЛЕНИЯ НАСОСОМ 💧 / 🔄 Роутер перезагружен
:global MsgSysReboot "%F0%9F%9A%B0%20%D0%A1%D0%98%D0%A1%D0%A2%D0%95%D0%9C%D0%90%20%D0%A3%D0%9F%D0%A0%D0%90%D0%92%D0%9B%D0%95%D0%9D%D0%98%D0%AF%20%D0%9D%D0%90%D0%A1%D0%9E%D0%A1%D0%9E%D0%9C%20%F0%9F%92%A7%0A%F0%9F%94%84%20%D0%A0%D0%BE%D1%83%D1%82%D0%B5%D1%80%20%D0%BF%D0%B5%D1%80%D0%B5%D0%B7%D0%B0%D0%B3%D1%80%D1%83%D0%B6%D0%B5%D0%BD"
# 🅾️ Насос отключен после перезагрузки
:global MsgSysPoeDisabled "%F0%9F%85%BE%EF%B8%8F%20%D0%9D%D0%B0%D1%81%D0%BE%D1%81%20%D0%BE%D1%82%D0%BA%D0%BB%D1%8E%D1%87%D0%B5%D0%BD%20%D0%BF%D0%BE%D1%81%D0%BB%D0%B5%20%D0%BF%D0%B5%D1%80%D0%B5%D0%B7%D0%B0%D0%B3%D1%80%D1%83%D0%B7%D0%BA%D0%B8"

# Системные уведомления
# ❌ Ошибка: 
:global MsgSysError "%E2%9D%8C%20%D0%9E%D1%88%D0%B8%D0%B1%D0%BA%D0%B0%3A%20"
# ⚠️ ВНИМАНИЕ: 
:global MsgSysWarning "%E2%9A%A0%EF%B8%8F%20%D0%92%D0%9D%D0%98%D0%9C%D0%90%D0%9D%D0%98%D0%95%3A%20"
# ✅ Успешно: 
:global MsgSysSuccess "%E2%9C%85%20%D0%A3%D1%81%D0%BF%D0%B5%D1%88%D0%BD%D0%BE%3A%20"

# ===== 2. СТАТУСЫ НАСОСА =====
# Основные статусы
# 🟢 Насос включен
:global MsgPumpOn "%F0%9F%9F%A2%20%D0%9D%D0%B0%D1%81%D0%BE%D1%81%20%D0%B2%D0%BA%D0%BB%D1%8E%D1%87%D0%B5%D0%BD"
# 🔴 Насос выключен
:global MsgPumpOff "%F0%9F%94%B4%20%D0%9D%D0%B0%D1%81%D0%BE%D1%81%20%D0%B2%D1%8B%D0%BA%D0%BB%D1%8E%D1%87%D0%B5%D0%BD"
# 🟢 Насос уже работает
:global MsgPumpAlreadyOn "%F0%9F%9F%A2%20%D0%9D%D0%B0%D1%81%D0%BE%D1%81%20%D1%83%D0%B6%D0%B5%20%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D0%B5%D1%82"

# Статусы остановки
# 🔴 Насос остановлен
:global MsgPumpStopped "%F0%9F%94%B4%20%D0%9D%D0%B0%D1%81%D0%BE%D1%81%20%D0%BE%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD"
# 🔴 Насос остановлен автоматически
:global MsgPumpAutoStop "%F0%9F%94%B4%20%D0%9D%D0%B0%D1%81%D0%BE%D1%81%20%D0%BE%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%20%D0%B0%D0%B2%D1%82%D0%BE%D0%BC%D0%B0%D1%82%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8"
# 🔴 Насос остановлен вручную
:global MsgPumpManualStop "%F0%9F%94%B4%20%D0%9D%D0%B0%D1%81%D0%BE%D1%81%20%D0%BE%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%20%D0%B2%D1%80%D1%83%D1%87%D0%BD%D1%83%D1%8E"
# 🔴 ОСТАНОВЛЕН ПО КОМАНДЕ
:global MsgPumpStoppedByCmd "%F0%9F%94%B4%20%D0%9E%D0%A1%D0%A2%D0%90%D0%9D%D0%9E%D0%92%D0%9B%D0%95%D0%9D%20%D0%9F%D0%9E%20%D0%9A%D0%9E%D0%9C%D0%90%D0%9D%D0%94%D0%95"
# 🔴 ОСТАНОВЛЕН - время уменьшено
:global MsgPumpStoppedTimeReduced "%F0%9F%94%B4%20%D0%9E%D0%A1%D0%A2%D0%90%D0%9D%D0%9E%D0%92%D0%9B%D0%95%D0%9D%20-%20%D0%B2%D1%80%D0%B5%D0%BC%D1%8F%20%D1%83%D0%BC%D0%B5%D0%BD%D1%8C%D1%88%D0%B5%D0%BD%D0%BE"

# Статусы запуска
# 🟢 НАСОС ЗАПУЩЕН на
:global MsgPumpStartedFor "%F0%9F%9F%A2%20%D0%9D%D0%90%D0%A1%D0%9E%D0%A1%20%D0%97%D0%90%D0%9F%D0%A3%D0%A9%D0%95%D0%9D%20%D0%BD%D0%B0"

# Шаблоны времени
# Работал 
:global MsgTimeWorked "%D0%A0%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D0%BB%20"
# Будет работать 
:global MsgTimeWillWork "%D0%91%D1%83%D0%B4%D0%B5%D1%82%20%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C%20"
# Общее время: 
:global MsgTimeTotal "%D0%9E%D0%B1%D1%89%D0%B5%D0%B5%20%D0%B2%D1%80%D0%B5%D0%BC%D1%8F%3A%20"
# Единицы времени
# минут 
:global MsgTimeMin "%20%D0%BC%D0%B8%D0%BD%D1%83%D1%82%20"
# секунд
:global MsgTimeSec "%20%D1%81%D0%B5%D0%BA%D1%83%D0%BD%D0%B4"

# ===== 3. МЕНЮ И КОМАНДЫ =====
# Заголовок меню
# 🖥️ Доступные команды:
:global MsgMenuHeader "%F0%9F%96%A5%EF%B8%8F%20%D0%94%D0%BE%D1%81%D1%82%D1%83%D0%BF%D0%BD%D1%8B%D0%B5%20%D0%BA%D0%BE%D0%BC%D0%B0%D0%BD%D0%B4%D1%8B%3A"

# Команды управления
# 🔴 Остановить насос
:global MsgMenuStop "%F0%9F%94%B4%20%D0%9E%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%B8%D1%82%D1%8C%20%D0%BD%D0%B0%D1%81%D0%BE%D1%81"
# 👁️ Показать статус
:global MsgMenuStatus "%F0%9F%91%81%EF%B8%8F%20%D0%9F%D0%BE%D0%BA%D0%B0%D0%B7%D0%B0%D1%82%D1%8C%20%D1%81%D1%82%D0%B0%D1%82%D1%83%D1%81"
# Команды запуска
# 5️⃣ Включить на 5 минут
:global MsgMenuStart5 "5%EF%B8%8F%E2%83%A3%20%D0%92%D0%BA%D0%BB%D1%8E%D1%87%D0%B8%D1%82%D1%8C%20%D0%BD%D0%B0%205%20%D0%BC%D0%B8%D0%BD%D1%83%D1%82"
# 🔟 Включить на 10 минут
:global MsgMenuStart10 "%F0%9F%94%9F%20%D0%92%D0%BA%D0%BB%D1%8E%D1%87%D0%B8%D1%82%D1%8C%20%D0%BD%D0%B0%2010%20%D0%BC%D0%B8%D0%BD%D1%83%D1%82"
# 3️⃣0️⃣ Включить на 30 минут
:global MsgMenuStart30 "3%EF%B8%8F%E2%83%A30%EF%B8%8F%E2%83%A3%20%D0%92%D0%BA%D0%BB%D1%8E%D1%87%D0%B8%D1%82%D1%8C%20%D0%BD%D0%B0%2030%20%D0%BC%D0%B8%D0%BD%D1%83%D1%82"
# 6️⃣0️⃣ Включить на 1 час
:global MsgMenuStart60 "6%EF%B8%8F%E2%83%A30%EF%B8%8F%E2%83%A3%20%D0%92%D0%BA%D0%BB%D1%8E%D1%87%D0%B8%D1%82%D1%8C%20%D0%BD%D0%B0%201%20%D1%87%D0%B0%D1%81"
# 1️⃣2️⃣0️⃣ Включить на 2 часа
:global MsgMenuStart120 "1%EF%B8%8F%E2%83%A32%EF%B8%8F%E2%83%A30%EF%B8%8F%E2%83%A3%20%D0%92%D0%BA%D0%BB%D1%8E%D1%87%D0%B8%D1%82%D1%8C%20%D0%BD%D0%B0%202%20%D1%87%D0%B0%D1%81%D0%B0"
# 📜 Показать меню
:global MsgMenuShow "%F0%9F%93%9C%20%D0%9F%D0%BE%D0%BA%D0%B0%D0%B7%D0%B0%D1%82%D1%8C%20%D0%BC%D0%B5%D0%BD%D1%8E"

# ===== 4. СТАТУСЫ И ЗАГОЛОВКИ =====
# Заголовки статусов
# 📱 Статус:
:global MsgStatusHeader "%F0%9F%93%B1%20%D0%A1%D1%82%D0%B0%D1%82%D1%83%D1%81%3A"
# Текущий статус: 
:global MsgStatusCurrent "%D0%A2%D0%B5%D0%BA%D1%83%D1%89%D0%B8%D0%B9%20%D1%81%D1%82%D0%B0%D1%82%D1%83%D1%81%3A%20"

# Индикаторы состояния
# 🟢 РАБОТАЕТ
:global MsgStatusRunning "%F0%9F%9F%A2%20%D0%A0%D0%90%D0%91%D0%9E%D0%A2%D0%90%D0%95%D0%A2"
# 🔴 ОСТАНОВЛЕН
:global MsgStatusStopped "%F0%9F%94%B4%20%D0%9E%D0%A1%D0%A2%D0%90%D0%9D%D0%9E%D0%92%D0%9B%D0%95%D0%9D"
# 🔄 Без автоматической остановки
:global MsgStatusNoAutoStop "%F0%9F%94%84%20%D0%91%D0%B5%D0%B7%20%D0%B0%D0%B2%D1%82%D0%BE%D0%BC%D0%B0%D1%82%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%BE%D0%B9%20%D0%BE%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BA%D0%B8"
# ⚠️ Таймер истек - скоро остановится
:global MsgStatusTimerExpired "%E2%9A%A0%EF%B8%8F%20%D0%A2%D0%B0%D0%B9%D0%BC%D0%B5%D1%80%20%D0%B8%D1%81%D1%82%D0%B5%D0%BA%20-%20%D1%81%D0%BA%D0%BE%D1%80%D0%BE%20%D0%BE%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%B8%D1%82%D1%81%D1%8F"

# Дополнительные статусы для команды status
# ⏱️ Работает: 
:global MsgStatusWorkingTime "%E2%8F%B1%EF%B8%8F%20%D0%A0%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D0%B5%D1%82%3A%20"
# ⏳ Останется: 
:global MsgStatusTimeLeft "%E2%8F%B3%20%D0%9E%D1%81%D1%82%D0%B0%D0%BD%D0%B5%D1%82%D1%81%D1%8F%3A%20"
# ⏱️ Остановлен: 
:global MsgStatusStoppedTime "%E2%8F%B1%EF%B8%8F%20%D0%9E%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%3A%20"
# назад
:global MsgStatusTimeAgo "%20%D0%BD%D0%B0%D0%B7%D0%B0%D0%B4"
# ❓ Время последней остановки неизвестно
:global MsgStatusLastStopUnknown "%E2%9D%93%20%D0%92%D1%80%D0%B5%D0%BC%D1%8F%20%D0%BF%D0%BE%D1%81%D0%BB%D0%B5%D0%B4%D0%BD%D0%B5%D0%B9%20%D0%BE%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BA%D0%B8%20%D0%BD%D0%B5%D0%B8%D0%B7%D0%B2%D0%B5%D1%81%D1%82%D0%BD%D0%BE"

# ===== 5. ВРЕМЯ И ТАЙМЕРЫ =====
# Шаблоны времени
# Работал 
:global MsgTimeWorked "%D0%A0%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D0%BB%20"
# Будет работать 
:global MsgTimeWillWork "%D0%91%D1%83%D0%B4%D0%B5%D1%82%20%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C%20"
# Общее время: 
:global MsgTimeTotal "%D0%9E%D0%B1%D1%89%D0%B5%D0%B5%20%D0%B2%D1%80%D0%B5%D0%BC%D1%8F%3A%20"

# Единицы времени
# минут 
:global MsgTimeMin "%20%D0%BC%D0%B8%D0%BD%D1%83%D1%82%20"
# секунд
:global MsgTimeSec "%20%D1%81%D0%B5%D0%BA%D1%83%D0%BD%D0%B4"

# Заголовки времени
# ⏳ Будет работать еще:
:global MsgTimeRemaining "%E2%8F%B3%20%D0%91%D1%83%D0%B4%D0%B5%D1%82%20%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C%20%D0%B5%D1%89%D0%B5%3A"
# ⚡️ Время уменьшено на
:global MsgTimeReduced "%E2%9A%A1%EF%B8%8F%20%D0%92%D1%80%D0%B5%D0%BC%D1%8F%20%D1%83%D0%BC%D0%B5%D0%BD%D1%8C%D1%88%D0%B5%D0%BD%D0%BE%20%D0%BD%D0%B0"
# ⏱️ Ожидаемое общее время работы:
:global MsgTimeExpectedTotal "%E2%8F%B1%EF%B8%8F%20%D0%9E%D0%B6%D0%B8%D0%B4%D0%B0%D0%B5%D0%BC%D0%BE%D0%B5%20%D0%BE%D0%B1%D1%89%D0%B5%D0%B5%20%D0%B2%D1%80%D0%B5%D0%BC%D1%8F%20%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D1%8B%3A"
# ⏱️ Работал:
:global MsgTimeWorkedHeader "%0A%E2%8F%B1%EF%B8%8F%20%D0%A0%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D0%BB%3A"

# ===== 6. СТОРОЖ =====
# Сообщения WatchDog
# 🔄 Сторож: Перезапуск модуля Telegram
:global MsgSysWatchdogRestart "%F0%9F%94%84%20%D0%A1%D1%82%D0%BE%D1%80%D0%BE%D0%B6%3A%20%D0%9F%D0%B5%D1%80%D0%B5%D0%B7%D0%B0%D0%BF%D1%83%D1%81%D0%BA%20%D0%BC%D0%BE%D0%B4%D1%83%D0%BB%D1%8F%20Telegram"
# 🔄 Сторож: Перезапуск после таймаута
:global MsgSysWatchdogTimeout "%F0%9F%94%84%20%D0%A1%D1%82%D0%BE%D1%80%D0%BE%D0%B6%3A%20%D0%9F%D0%B5%D1%80%D0%B5%D0%B7%D0%B0%D0%BF%D1%83%D1%81%D0%BA%20%D0%BF%D0%BE%D1%81%D0%BB%D0%B5%20%D1%82%D0%B0%D0%B9%D0%BC%D0%B0%D1%83%D1%82%D0%B0"

# ===== 7. ШАБЛОНЫ КОМАНД =====
# Шаблон команды остановки
:global MsgStopCmdTemplate ":local sendTelegram do={\r\
    :global BotToken;\r\
    :global ChatId;\r\
    \$sendTelegram \$BotToken \$ChatId (\$MsgSysStarted . \$MsgNewLine . \$MsgStatusCurrent . \$MsgNewLine . \$MsgPumpAutoStop . \$telegramWorkMsg)\r\
}\r\
:global NasosInitStatus;\r\
:global PoeActiveTimer;\r\
:global PoeStartTime;\r\
:global PoeMainInterface;\r\
:global LastStopTime;\r\
:if ([:typeof \$NasosInitStatus] = \"nothing\" || !\$NasosInitStatus) do {\r\
    :error \"Насос не инициализирован\";\r\
}\r\
:if ([:len \$PoeStartTime] > 0) do {\r\
    :local workSeconds ([:timestamp] - \$PoeStartTime);\r\
    :local workMinutes ((\$workSeconds - (\$workSeconds % 60)) / 60);\r\
    :local workSecondsRem (\$workSeconds % 60);\r\
    :set telegramWorkMsg (\$MsgNewLine . \$MsgTimeWorked . [:tostr \$workMinutes] . \$MsgTimeMin . [:tostr \$workSecondsRem] . \$MsgTimeSec);\r\
}\r\
/interface ethernet set [find name=\$PoeMainInterface] poe-out=off;\r\
:set LastStopTime [:timestamp];\r\
:set PoeStartTime \"\";\r\
:set PoeActiveTimer \"\";\r\
\$sendTelegram"
