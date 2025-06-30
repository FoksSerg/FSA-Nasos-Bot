# Boler-LevelSensor.rsc v3.2 - Человекочитаемые статусы в логе
# Автор: Фокин Сергей Александрович
# Дата: 28 июня 2025
# Описание: Вечный цикл, статусы в логе на русском

:log info "BOLER-SENSOR: Запуск простого вечного цикла мониторинга уровня воды"

# Глобальные переменные (объявляются сразу!)
:global BolerWorkLevelStatus false
:global BolerCriticalLevelStatus false
:global BolerSensorReliable false
:global BolerLastSensorUpdate "никогда"

# Настройки
:local portName "E5-Level"
:local interval 10

:do {
    :while (true) do={
        :local workResult "unknown"
        :local criticalResult "unknown"
        :local reliable false

        :do {
            /interface ethernet cable-test $portName duration=1
            :delay 2s
            :local cableTestResult [/interface ethernet cable-test $portName once as-value]
            :if ([:len $cableTestResult] > 0) do={
                :local cablePairs ($cableTestResult->"cable-pairs")
                :if ([:len $cablePairs] >= 2) do={
                    :local pair1Status [:pick $cablePairs 0]
                    :local pair2Status [:pick $cablePairs 1]
                    :if ($pair1Status ~ "shorted") do={ :set criticalResult "not-reached" } else={ :if ($pair1Status ~ "open") do={ :set criticalResult "reached" } else={ :set criticalResult "error" } }
                    :if ($pair2Status ~ "shorted") do={ :set workResult "not-reached" } else={ :if ($pair2Status ~ "open") do={ :set workResult "reached" } else={ :set workResult "error" } }
                    :if (($workResult != "error") && ($criticalResult != "error")) do={ :set reliable true }
                }
            }
        } on-error={ :log error "BOLER-SENSOR: Ошибка выполнения cable-test" }

        # Обновляем глобальные переменные (явно!)
        :set BolerWorkLevelStatus ($workResult = "reached")
        :set BolerCriticalLevelStatus ($criticalResult = "reached")
        :set BolerSensorReliable $reliable
        :set BolerLastSensorUpdate [/system clock get time]

        # Преобразуем статусы в человекочитаемые
        :local workText "ОШИБКА"
        :local criticalText "ОШИБКА"
        :local reliableText "Недостоверно"
        :if ($workResult = "reached") do={ :set workText "НОРМА" } else={ :if ($workResult = "not-reached") do={ :set workText "НЕ ДОСТИГНУТ" } }
        :if ($criticalResult = "reached") do={ :set criticalText "АВАРИЯ ПЕРЕЛИВ" } else={ :if ($criticalResult = "not-reached") do={ :set criticalText "НОРМА" } }
        :if ($reliable) do={ :set reliableText "Достоверно" }

        :log info ("BOLER-SENSOR: Рабочий=" . $workText . ", Критический=" . $criticalText . ", " . $reliableText)

        :delay $interval
    }
} on-error={ :log error "BOLER-SENSOR: Критическая ошибка, цикл остановлен" }