:global NasosSSHUser "Nasos";
:foreach k in=[/user ssh-keys find user="Nasos"] do={ /user ssh-keys remove $k }
:if ([:len [/file find name="boler_rsa_pub.pem"]] > 0) do={
:do {
/user ssh-keys import public-key-file=boler_rsa_pub.pem user=$NasosSSHUser;
:log info "NASOS-SSH-INSTALL: Публичный ключ Бойлера успешно импортирован";
} on-error={
:log error "NASOS-SSH-INSTALL: Ошибка импорта публичного ключа Бойлера";
}
} else={
:log error "NASOS-SSH-INSTALL: Файл boler_rsa_pub.pem не найден";
}
