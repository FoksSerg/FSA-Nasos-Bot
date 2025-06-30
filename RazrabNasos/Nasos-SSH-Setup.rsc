# ===== NASOS-SSH-SETUP =====
# Полная инициализация SSH для обмена с Бойлером (RouterOS 7+)
# Создание пользователя, генерация PEM-ключей, тестовая переменная и скрипт

:log warning "Начинаем создание ключей NASOS-SSH"

# Удаляем все старые ключи пользователя Nasos и файлы ключей
:foreach k in=[/user ssh-keys find user="Nasos"] do={ /user ssh-keys remove $k }
:foreach f in=[/file find name~"nasos"] do={ 
    :log info ("NASOS-SSH: Удаляю старый файл: " . [/file get $f name])
    /file remove $f 
}

# Создаём или обновляем пользователя Nasos
:if ([:len [/user find name="Nasos"]] = 0) do={
    /user add name=Nasos group=full password=nasos
} else={
    /user set [find name="Nasos"] group=full password=nasos
}

# Генерируем новые SSH-ключи
:log info "NASOS-SSH: Генерируем новые ключи"
/ip ssh export-host-key key-file-prefix=nasos
:delay 3

# Универсальная логика создания стандартных ключей (RouterOS 7.12.1 и 7.19.1)
:log info "NASOS-SSH: Анализируем созданные файлы"
:local privateKey ""
:local publicKey ""
:foreach f in=[/file find name~"nasos"] do={
    :local fname [/file get $f name]
    :log info ("NASOS-SSH: Найден файл: " . $fname)
    :if ($fname ~ "_rsa\\.pem\$") do={ 
        :set privateKey $fname
        :log info "NASOS-SSH: Это приватный ключ"
    }
    :if ($fname ~ "_rsa\\.pem\\.pub\$") do={ 
        :set publicKey $fname
        :log info "NASOS-SSH: Это публичный ключ .pem.pub (RouterOS 7.12.1)"
    }
    :if ($fname ~ "_rsa_pub\\.pem\$") do={ 
        :set publicKey $fname
        :log info "NASOS-SSH: Это публичный ключ _pub.pem (RouterOS 7.19.1)"
    }
}

# Создаём стандартный публичный ключ с расширением .pem (только для RouterOS 7.12.1)
:if ([:len $publicKey] > 0 && $publicKey ~ "\\.pub\$") do={
    :log info ("NASOS-SSH: Копируем публичный: " . $publicKey . " -> nasos_rsa_pub.pem")
    /file add name="nasos_rsa_pub.pem" contents=[/file get $publicKey contents]
    
    :log info ("NASOS-SSH: Удаляем временный: " . $publicKey)
    /file remove $publicKey
} else={
    :log info "NASOS-SSH: Публичный ключ уже в правильном формате"
}

# Проверяем, что ключи созданы и доступны
:local pemFile [/file find name="nasos_rsa.pem"]
:local pubFile [/file find name="nasos_rsa_pub.pem"]
:if ([:len $pemFile] > 0 && [:len $pubFile] > 0) do={
    :log info "NASOS-SSH: SSH ключи успешно созданы и готовы к использованию"
} else={
    :log error "NASOS-SSH: Ошибка создания SSH ключей"
}

# Тестовая переменная
:global NasosTestVar ("Я Насос " . [/system clock get time])

# Удаляем старый тестовый скрипт (если есть)
:if ([:len [/system script find name="Nasos-SSH-Test"]] > 0) do={
    /system script remove "Nasos-SSH-Test"
    :log info "NASOS-SSH: Удален старый тестовый скрипт"
}

# Тестовый скрипт для вывода своей переменной и переменной с бойлера в лог
/system script add name="Nasos-SSH-Test" source={
    :global NasosTestVar;
    :set NasosTestVar ("Я Насос " . [/system clock get time]);
    :log info ("NASOS-SSH-TEST: NasosTestVar=" . $NasosTestVar);
    :local sshResult ([/system ssh-exec address=10.10.44.1 user=Nasos command=":put \$BolerTestVar" as-value]->"output");
    :log info ("NASOS-SSH-TEST: BolerTestVar с бойлера: " . $sshResult);
}

# Импорт приватного ключа и назначение пользователю
:log info "NASOS-SSH: Импортируем приватный ключ"
/user ssh-keys private import private-key-file=nasos_rsa.pem user=Nasos
:delay 1

# Проверяем импорт ключа
:local importedKeys [/user ssh-keys private find user="Nasos"]
:if ([:len $importedKeys] > 0) do={
    :log info "NASOS-SSH: Приватный ключ успешно импортирован и назначен пользователю Nasos"
} else={
    :log error "NASOS-SSH: Ошибка импорта приватного ключа"
}

:log info "NASOS-SSH-SETUP: Завершено успешно" 