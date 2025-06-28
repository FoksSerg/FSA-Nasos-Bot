# NASOS SSH TEST - Тестирование SSH-соединения к Boler
# Этот скрипт тестирует SSH-соединение от роутера Nasos к роутеру Boler
# и проверяет возможность получения данных о состоянии датчиков.
#
# Функции:
# 1. Тест базового SSH-соединения
# 2. Проверка доступности переменных Boler
# 3. Тест получения статуса датчиков
# 4. Диагностика проблем подключения
#
# Автор: NasosRunner Project
# Версия: 1.0

:log info "NASOS-SSH-TEST: Начинаем тестирование SSH-соединения к Boler"

# === ПАРАМЕТРЫ ПОДКЛЮЧЕНИЯ ===
:local bolerIP "10.10.55.2"
:local bolerUser "FokinSA"
:local sshKeyName "nasos-to-boler"

:log info ("NASOS-SSH-TEST: Тестируем подключение к: " . $bolerIP)
:log info ("NASOS-SSH-TEST: Пользователь: " . $bolerUser)

# === ТЕСТ 1: БАЗОВОЕ SSH-СОЕДИНЕНИЕ ===
:log info "NASOS-SSH-TEST: Тест 1 - Базовое SSH-соединение"

:local testResult ""
:local testError ""

:do {
    :set testResult [/system ssh-exec address=$bolerIP user=$bolerUser command=":put 'SSH-соединение работает'"]
    :log info ("NASOS-SSH-TEST: Базовое соединение успешно: " . $testResult)
} on-error={
    :set testError $error
    :log error ("NASOS-SSH-TEST: Ошибка базового соединения: " . $testError)
    :log error "NASOS-SSH-TEST: Проверьте настройки SSH на обоих роутерах"
    :error "SSH-соединение не работает"
}

# === ТЕСТ 2: ПРОВЕРКА СИСТЕМНОЙ ИНФОРМАЦИИ ===
:log info "NASOS-SSH-TEST: Тест 2 - Системная информация Boler"

:do {
    :set testResult [/system ssh-exec address=$bolerIP user=$bolerUser command=":put [/system identity get name]"]
    :log info ("NASOS-SSH-TEST: Идентификация роутера: " . $testResult)
} on-error={
    :set testError $error
    :log warning ("NASOS-SSH-TEST: Ошибка получения системной информации: " . $testError)
}

# === ТЕСТ 3: ПРОВЕРКА ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ BOLER ===
:log info "NASOS-SSH-TEST: Тест 3 - Проверка глобальных переменных Boler"

# Список переменных для проверки
:local bolerVars ("BolerLevel1", "BolerLevel2", "BolerLevel3", "BolerStatus", "BolerReliability")

:foreach varName in=$bolerVars do={
    :do {
        :set testResult [/system ssh-exec address=$bolerIP user=$bolerUser command=(":put \$" . $varName)]
        :log info ("NASOS-SSH-TEST: Переменная " . $varName . ": " . $testResult)
    } on-error={
        :log warning ("NASOS-SSH-TEST: Переменная " . $varName . " не найдена или недоступна")
    }
}

# === ТЕСТ 4: ПРОВЕРКА СКРИПТОВ BOLER ===
:log info "NASOS-SSH-TEST: Тест 4 - Проверка скриптов Boler"

:do {
    :set testResult [/system ssh-exec address=$bolerIP user=$bolerUser command="/system script print count-only where name~\"Boler\""]
    :log info ("NASOS-SSH-TEST: Найдено скриптов Boler: " . $testResult)
} on-error={
    :set testError $error
    :log warning ("NASOS-SSH-TEST: Ошибка проверки скриптов: " . $testError)
}

# === ТЕСТ 5: ТЕСТИРОВАНИЕ КОМАНДЫ ПОЛУЧЕНИЯ СТАТУСА ===
:log info "NASOS-SSH-TEST: Тест 5 - Тестирование команды получения статуса"

:local statusCommand ":put (\"BOLER-STATUS: Level1=\" . \$BolerLevel1 . \" Level2=\" . \$BolerLevel2 . \" Level3=\" . \$BolerLevel3 . \" Status=\" . \$BolerStatus . \" Reliability=\" . \$BolerReliability)"

:do {
    :set testResult [/system ssh-exec address=$bolerIP user=$bolerUser command=$statusCommand]
    :log info ("NASOS-SSH-TEST: Статус датчиков: " . $testResult)
} on-error={
    :set testError $error
    :log warning ("NASOS-SSH-TEST: Ошибка получения статуса: " . $testError)
}

# === ТЕСТ 6: ПРОВЕРКА СЕТЕВОЙ ДОСТУПНОСТИ ===
:log info "NASOS-SSH-TEST: Тест 6 - Проверка сетевой доступности"

:do {
    :set testResult [/ping count=3 $bolerIP]
    :log info ("NASOS-SSH-TEST: Сетевая доступность: " . $testResult)
} on-error={
    :set testError $error
    :log warning ("NASOS-SSH-TEST: Проблемы с сетевой доступностью: " . $testError)
}

# === ДИАГНОСТИКА SSH-КЛЮЧЕЙ ===
:log info "NASOS-SSH-TEST: Диагностика SSH-ключей"

:local keyExists [/ssh key print count-only where name=$sshKeyName]
:log info ("NASOS-SSH-TEST: SSH-ключей " . $sshKeyName . ": " . $keyExists)

:local clientExists [/ssh client print count-only where address=$bolerIP]
:log info ("NASOS-SSH-TEST: SSH-клиентов для " . $bolerIP . ": " . $clientExists)

# === ИТОГОВЫЙ ОТЧЕТ ===
:log info "NASOS-SSH-TEST: РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ SSH"
:log info ("Целевой роутер: " . $bolerIP)
:log info ("Пользователь: " . $bolerUser)
:log info ("SSH-ключ: " . $sshKeyName)
:log info ""
:log info "Если все тесты прошли успешно:"
:log info "SSH-соединение работает корректно"
:log info "Можно использовать Boler-NetworkAPI.rsc"
:log info "Система готова к автоматическому опросу датчиков"
:log info ""
:log info "Если есть ошибки:"
:log info "Проверьте настройки SSH на обоих роутерах"
:log info "Убедитесь что публичный ключ импортирован на Boler"
:log info "Проверьте сетевую доступность между роутерами"

:log info "NASOS-SSH-TEST: Тестирование SSH завершено" 