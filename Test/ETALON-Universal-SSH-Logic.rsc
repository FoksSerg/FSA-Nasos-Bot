# ===============================================
# ЭТАЛОННЫЙ КОД УНИВЕРСАЛЬНОЙ ЛОГИКИ SSH-КЛЮЧЕЙ
# ===============================================
# Протестирован и работает на RouterOS 7.12.1 и 7.19.1
# Автоматически определяет формат файлов ключей и создает стандартные копии
# Удаляет все временные файлы, оставляя только нужные
# ===============================================

:log info "=== УНИВЕРСАЛЬНАЯ ЛОГИКА SSH-КЛЮЧЕЙ ==="
:log info "0. Очищаем старые ключи (если есть)"
:foreach f in=[/file find name~"test-universal"] do={
    :local fname [/file get $f name]
    :log info ("Удаляем старый файл: " . $fname)
    /file remove $f
}
:delay 1

:log info "1. Генерируем ключи"
/ip ssh export-host-key key-file-prefix=test-universal
:delay 3

:log info "2. Анализируем созданные файлы"
:local privateKey ""
:local publicKey ""
:foreach f in=[/file find name~"test-universal"] do={
    :local fname [/file get $f name]
    :log info ("Найден файл: " . $fname)
    :if ($fname ~ "_rsa\\.pem\$") do={ 
        :set privateKey $fname
        :log info "  -> Это приватный ключ"
    }
    :if ($fname ~ "_rsa\\.pem\\.pub\$") do={ 
        :set publicKey $fname
        :log info "  -> Это публичный ключ .pem.pub (RouterOS 7.12.1)"
    }
    :if ($fname ~ "_rsa_pub\\.pem\$") do={ 
        :set publicKey $fname
        :log info "  -> Это публичный ключ _pub.pem (RouterOS 7.19.1)"
    }
}

:log info "3. Создаём стандартные копии"
:if ([:len $privateKey] > 0) do={
    :log info ("Копируем приватный: " . $privateKey . " -> test-universal_final.pem")
    /file add name="test-universal_final.pem" contents=[/file get $privateKey contents]
}
:if ([:len $publicKey] > 0) do={
    :log info ("Копируем публичный: " . $publicKey . " -> test-universal_final_pub.pem")
    /file add name="test-universal_final_pub.pem" contents=[/file get $publicKey contents]
}

:log info "4. Удаляем временные файлы"
:if ([:len $privateKey] > 0) do={
    :log info ("Удаляем: " . $privateKey)
    /file remove $privateKey
}
:if ([:len $publicKey] > 0) do={
    :log info ("Удаляем: " . $publicKey)
    /file remove $publicKey
}

:log info "5. Проверяем финальный результат"
:if ([:len [/file find name="test-universal_final.pem"]] > 0 && [:len [/file find name="test-universal_final_pub.pem"]] > 0) do={
    :log info "УСПЕХ: Все ключи в стандартном формате, временные файлы удалены"
} else={
    :log error "ОШИБКА: Не все ключи созданы"
}
:log info "=== УНИВЕРСАЛЬНАЯ ЛОГИКА ЗАВЕРШЕНА ==="

# ===============================================
# РЕЗУЛЬТАТ: Остаются только файлы:
# - test-universal_final.pem (приватный ключ)
# - test-universal_final_pub.pem (публичный ключ)
# =============================================== 