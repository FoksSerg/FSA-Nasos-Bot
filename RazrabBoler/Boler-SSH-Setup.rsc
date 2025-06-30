# ===== BOLER-SSH-SETUP =====
# Полная инициализация SSH для обмена с Насосом (RouterOS 7+)
# Создание пользователя, генерация PEM-ключей, тестовая переменная и скрипт

:log warning "Начинаем создание ключей BOLER-SSH"

# Удаляем все старые ключи пользователя Nasos и файлы ключей
:foreach k in=[/user ssh-keys find user="Nasos"] do={ /user ssh-keys remove $k }
:foreach f in=[/file find name~"boler"] do={ 
    :log info ("BOLER-SSH: Удаляю старый файл: " . [/file get $f name])
    /file remove $f 
}

# Создаём или обновляем пользователя Nasos
:if ([:len [/user find name="Nasos"]] = 0) do={
    /user add name=Nasos group=full password=nasos
} else={
    /user set [find name="Nasos"] group=full password=nasos
}

# Генерируем новые SSH-ключи
:log info "BOLER-SSH: Генерируем новые ключи"
/ip ssh export-host-key key-file-prefix=boler
:delay 3

# Универсальная логика создания стандартных ключей (RouterOS 7.12.1 и 7.19.1)
:log info "BOLER-SSH: Анализируем созданные файлы"
:local privateKey ""
:local publicKey ""
:foreach f in=[/file find name~"boler"] do={
    :local fname [/file get $f name]
    :log info ("BOLER-SSH: Найден файл: " . $fname)
    :if ($fname ~ "_rsa\\.pem\$") do={ 
        :set privateKey $fname
        :log info "BOLER-SSH: Это приватный ключ"
    }
    :if ($fname ~ "_rsa\\.pem\\.pub\$") do={ 
        :set publicKey $fname
        :log info "BOLER-SSH: Это публичный ключ .pem.pub (RouterOS 7.12.1)"
    }
    :if ($fname ~ "_rsa_pub\\.pem\$") do={ 
        :set publicKey $fname
        :log info "BOLER-SSH: Это публичный ключ _pub.pem (RouterOS 7.19.1)"
    }
}

# Создаём стандартный публичный ключ с расширением .pem (только для RouterOS 7.12.1)
:if ([:len $publicKey] > 0 && $publicKey ~ "\\.pub\$") do={
    :log info ("BOLER-SSH: Копируем публичный: " . $publicKey . " -> boler_rsa_pub.pem")
    /file add name="boler_rsa_pub.pem" contents=[/file get $publicKey contents]
    
    :log info ("BOLER-SSH: Удаляем временный: " . $publicKey)
    /file remove $publicKey
} else={
    :log info "BOLER-SSH: Публичный ключ уже в правильном формате"
}

# Проверяем, что ключи созданы и доступны
:local pemFile [/file find name="boler_rsa.pem"]
:local pubFile [/file find name="boler_rsa_pub.pem"]
:if ([:len $pemFile] > 0 && [:len $pubFile] > 0) do={
    :log info "BOLER-SSH: SSH ключи успешно созданы и готовы к использованию"
} else={
    :log error "BOLER-SSH: Ошибка создания SSH ключей"
}

# Тестовая переменная
:global BolerTestVar ("Я Бойлер " . [/system clock get time])

# Удаляем старый тестовый скрипт (если есть)
:if ([:len [/system script find name="Boler-SSH-Test"]] > 0) do={
    /system script remove "Boler-SSH-Test"
    :log info "BOLER-SSH: Удален старый тестовый скрипт"
}

# Тестовый скрипт для вывода своей переменной и переменной с насоса в лог
/system script add name="Boler-SSH-Test" source={
    :global BolerTestVar;
    :set BolerTestVar ("Я Бойлер " . [/system clock get time]);
    :log info ("BOLER-SSH-TEST: BolerTestVar=" . $BolerTestVar);
    :local sshResult ([/system ssh-exec address=10.10.55.1 user=Nasos command=":put \$NasosTestVar" as-value]->"output");
    :log info ("BOLER-SSH-TEST: NasosTestVar с насоса: " . $sshResult);
}

# Импорт приватного ключа и назначение пользователю
:log info "BOLER-SSH: Импортируем приватный ключ"
/user ssh-keys private import private-key-file=boler_rsa.pem user=Nasos
:delay 1

# Проверяем импорт ключа
:local importedKeys [/user ssh-keys private find user="Nasos"]
:if ([:len $importedKeys] > 0) do={
    :log info "BOLER-SSH: Приватный ключ успешно импортирован и назначен пользователю Nasos"
} else={
    :log error "BOLER-SSH: Ошибка импорта приватного ключа"
}

:log info "BOLER-SSH-SETUP: Завершено успешно" 