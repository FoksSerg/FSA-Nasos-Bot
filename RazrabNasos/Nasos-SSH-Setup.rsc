# NASOS SSH SETUP (host key) - Настройка SSH для подключения к Boler
# Этот скрипт готовит host key для авторизации по ключу между роутерами.
#
# 1. Генерирует host key (RSA 4096)
# 2. Экспортирует приватный и публичный ключи в файлы
# 3. Инструктирует пользователя скопировать ключи на Boler
# 4. Не использует /ssh key generate
#
# Автор: NasosRunner Project
# Версия: 2.0

:log info "NASOS-SSH: Экспортируем host key для SSH-клиента (RSA 4096)"

# === ЭКСПОРТ HOST KEY ===
/ip ssh export-host-key key-file-prefix=nasos
:log info "NASOS-SSH: Host key экспортирован: nasos_rsa (приватный), nasos_rsa.pub (публичный)"

:log info "NASOS-SSH: Скопируйте nasos_rsa и nasos_rsa.pub на Boler (WinBox → Files, FTP, SCP, USB)"
:log info "NASOS-SSH: Импортируйте приватный ключ как admin_rsa, публичный — admin_rsa.pub для пользователя с полными правами"
:log info "NASOS-SSH: После копирования проверьте подключение: /system ssh address=10.10.55.1 user=FokinSA"
:log info "NASOS-SSH: Если пароль не запрашивается — всё настроено верно" 