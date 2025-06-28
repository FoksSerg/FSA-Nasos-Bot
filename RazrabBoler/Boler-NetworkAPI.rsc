# Boler-NetworkAPI.rsc - Опрос состояния насоса через API
# Автор: Фокин Сергей Александрович
# Дата: 28 июня 2025
# Описание: Однократный опрос состояния роутера Nasos, логирование с меткой NASOS-NETWORK

# Явно объявляем глобальные переменные
:global BolerNasosIP
:global BolerNasosUser
:global BolerNasosPassword
:global BolerNasosPort
:global BolerNasosConnection
:global BolerNasosStatus
:global BolerLastNasosUpdate

:local ip $BolerNasosIP
:local user $BolerNasosUser
:local pass $BolerNasosPassword
:local port $BolerNasosPort


:log info ("NASOS-NETWORK: DEBUG: ip=" . $BolerNasosIP . ", user=" . $BolerNasosUser . ", port=" . $BolerNasosPort)
:log info ("NASOS-NETWORK: Запуск опроса состояния насоса по адресу " . $ip)

:local success false
:local nasosStatus "unknown"

:do {
    # Пробуем подключиться к Nasos через API
    /tool fetch \
        url=("http://" . $ip . ":" . $port . "/login?name=" . $user . "&password=" . $pass) \
        mode=http keep-result=no as-value output=none
    :set success true
    :log info "NASOS-NETWORK: Соединение с Nasos установлено"
    
    # Пробуем получить переменную состояния (пример: NasosStatus)
    :do {
        /tool fetch \
            url=("http://" . $ip . ":" . $port . "/command=/system/script/environment/print?name=NasosStatus") \
            mode=http keep-result=yes as-value output=user
        :local result [/file get [find name~"fetch"] contents]
        :set nasosStatus $result
        :log info ("NASOS-NETWORK: Получено состояние насоса: " . $nasosStatus)
        /file remove [find name~"fetch"]
    } on-error={
        :log error "NASOS-NETWORK: Ошибка получения состояния насоса"
    }
} on-error={
    :set success false
    :log error "NASOS-NETWORK: Не удалось подключиться к Nasos по API"
}

# Обновляем глобальные переменные
:set BolerNasosConnection $success
:set BolerNasosStatus $nasosStatus
:if ($success) do={ :set BolerLastNasosUpdate [/system clock get time] } 