:log info "BOLER-SSH-TEST: Начинаем тестирование SSH-сервера";
:local nasosIP "10.10.55.1";
:local nasosUser "FokinSA";
:local sshKeyName "nasos-to-boler";
:log info ("BOLER-SSH-TEST: Ожидаем подключения от: " . $nasosIP);
:log info ("BOLER-SSH-TEST: Пользователь: " . $nasosUser);
:log info "BOLER-SSH-TEST: Тест 1 - Состояние SSH-сервера";
:local sshService [/ip service print where name=ssh];
:log info ("BOLER-SSH-TEST: SSH-сервис: " . $sshService);
:local sshEnabled [/ip service get ssh disabled];
if ($sshEnabled = false) do={
:log info "BOLER-SSH-TEST: SSH-сервер включен";
} else={
:log error "BOLER-SSH-TEST: SSH-сервер отключен";
:log error "BOLER-SSH-TEST: Включите SSH-сервер: /ip service set ssh disabled=no";
}
:log info "BOLER-SSH-TEST: Тест 2 - Настройки SSH-сервера";
:local sshVersion [/ip ssh get version];
:log info ("BOLER-SSH-TEST: SSH версия: " . $sshVersion);
:local strongCrypto [/ip ssh get strong-crypto];
:log info ("BOLER-SSH-TEST: Сильное шифрование: " . $strongCrypto);
:log info ("BOLER-SSH-TEST: Тест 3 - Проверка пользователя " . $nasosUser);
:local userExists [/user print count-only where name=$nasosUser];
if ($userExists > 0) do={
:log info ("BOLER-SSH-TEST: Пользователь " . $nasosUser . " найден");
:local userGroup [/user get $nasosUser group];
:log info ("BOLER-SSH-TEST: Группа пользователя: " . $userGroup);
:local userKeys [/user ssh-keys print count-only where user=$nasosUser];
:log info ("BOLER-SSH-TEST: SSH-ключей у пользователя: " . $userKeys);
} else={
:log error ("BOLER-SSH-TEST: Пользователь " . $nasosUser . " не найден");
:log error "BOLER-SSH-TEST: Создайте пользователя или используйте существующего";
}
:log info ("BOLER-SSH-TEST: Тест 4 - Проверка SSH-ключа " . $sshKeyName);
:local publicKeyExists [/ssh public-key print count-only where name=$sshKeyName];
if ($publicKeyExists > 0) do={
:log info ("BOLER-SSH-TEST: Публичный ключ " . $sshKeyName . " найден");
:local keyType [/ssh public-key get $sshKeyName key-type];
:log info ("BOLER-SSH-TEST: Тип ключа: " . $keyType);
} else={
:log error ("BOLER-SSH-TEST: Публичный ключ " . $sshKeyName . " не найден");
:log error "BOLER-SSH-TEST: Импортируйте публичный ключ от роутера Nasos";
}
:log info "BOLER-SSH-TEST: Тест 5 - Проверка глобальных переменных";
:local bolerVars ("BolerLevel1", "BolerLevel2", "BolerLevel3", "BolerStatus", "BolerReliability");
:foreach varName in=$bolerVars do={
:if ([:typeof [:global $varName]] != "nothing") do={
:local varValue [:global $varName];
:log info ("BOLER-SSH-TEST: Переменная " . $varName . ": " . $varValue);
} else={
:log warning ("BOLER-SSH-TEST: Переменная " . $varName . " не определена");
}
}
:log info "BOLER-SSH-TEST: Тест 6 - Проверка скриптов Boler";
:local bolerScripts (/system script print where name~"Boler");
:log info ("BOLER-SSH-TEST: Найдено скриптов Boler: " . [:len $bolerScripts]);
:foreach script in=$bolerScripts do={
:local scriptName [/system script get $script name];
:log info ("BOLER-SSH-TEST: Скрипт: " . $scriptName);
}
:log info "BOLER-SSH-TEST: Тест 7 - Проверка сетевой доступности";
:do {
:local pingResult [/ping count=3 $nasosIP];
:log info ("BOLER-SSH-TEST: Сетевая доступность к Nasos: " . $pingResult);
} on-error={
:log warning ("BOLER-SSH-TEST: Проблемы с сетевой доступностью к " . $nasosIP);
}
:log info "BOLER-SSH-TEST: Тест 8 - Локальный тест SSH-соединения";
:do {
:local localTest [/system ssh-exec address="127.0.0.1" user=$nasosUser command=":put 'Локальный SSH-тест успешен'"];
:log info ("BOLER-SSH-TEST: Локальный SSH-тест: " . $localTest);
} on-error={
:log warning ("BOLER-SSH-TEST: Локальный SSH-тест не прошел");
}
:log info "BOLER-SSH-TEST: Диагностика безопасности";
:local firewallRules [/ip firewall filter print count-only where chain=input and dst-port=22];
:log info ("BOLER-SSH-TEST: Правил файрвола для SSH: " . $firewallRules);
:local allowedAddresses [/ip service get ssh address];
:log info ("BOLER-SSH-TEST: Разрешенные адреса для SSH: " . $allowedAddresses);
:log info "BOLER-SSH-TEST: РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ SSH-СЕРВЕРА";
:log info ("Ожидаем подключения от: " . $nasosIP);
:log info ("Пользователь: " . $nasosUser);
:log info ("SSH-ключ: " . $sshKeyName);
:log info "";
:log info "Если все тесты прошли успешно:";
:log info "SSH-сервер готов к приему подключений";
:log info "Публичный ключ импортирован";
:log info "Пользователь настроен";
:log info "Глобальные переменные доступны";
:log info "";
:log info "Если есть ошибки:";
:log info "Включите SSH-сервер: /ip service set ssh disabled=no";
:log info "Импортируйте публичный ключ от Nasos";
:log info "Настройте пользователя и его права";
:log info "Проверьте настройки файрвола";
:log info "BOLER-SSH-TEST: Тестирование SSH-сервера завершено";
