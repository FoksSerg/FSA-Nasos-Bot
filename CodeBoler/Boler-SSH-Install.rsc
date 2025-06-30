:global BolerSSHUser "Nasos";
:foreach k in=[/user ssh-keys find user="Nasos"] do={ /user ssh-keys remove $k }
:if ([:len [/file find name="nasos_rsa_pub.pem"]] > 0) do={
:do {
/user ssh-keys import public-key-file=nasos_rsa_pub.pem user=$BolerSSHUser;
:log info "BOLER-SSH-INSTALL: Публичный ключ Насоса успешно импортирован";
} on-error={
:log error "BOLER-SSH-INSTALL: Ошибка импорта публичного ключа Насоса";
}
} else={
:log error "BOLER-SSH-INSTALL: Файл nasos_rsa_pub.pem не найден";
}
