# BOLER SSH SETUP (host key) - Настройка SSH-сервера для приема ключей
# Этот скрипт включает SSH, разрешает пароли, даёт инструкции по firewall и импорту ключей.
# Автор: NasosRunner Project
# Версия: 2.0

:log info "BOLER-SSH: Включаем SSH-сервер и разрешаем пароли для первого входа"
/ip service set ssh disabled=no
/ip ssh set always-allow-password-login=yes
:log info "BOLER-SSH: SSH-сервер включен, пароли разрешены"

:log info "BOLER-SSH: Импортируйте ключи admin_rsa и admin_rsa.pub через WinBox → Files или CLI"
:log info "BOLER-SSH: Привяжите публичный ключ к пользователю с полными правами через WinBox или CLI"
:log info "BOLER-SSH: После успешного подключения отключите пароли: /ip ssh set always-allow-password-login=no" 