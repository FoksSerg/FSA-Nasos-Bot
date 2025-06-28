:log info "NASOS-SSH: Экспортируем host key для SSH-клиента (RSA 4096)";
/ip ssh export-host-key key-file-prefix=nasos;
:log info "NASOS-SSH: Host key экспортирован: nasos_rsa (приватный), nasos_rsa.pub (публичный)";
:log info "NASOS-SSH: Скопируйте nasos_rsa и nasos_rsa.pub на Boler (WinBox → Files, FTP, SCP, USB)";
:log info "NASOS-SSH: Импортируйте приватный ключ как admin_rsa, публичный — admin_rsa.pub для пользователя с полными правами";
:log info "NASOS-SSH: После копирования проверьте подключение: /system ssh address=10.10.55.1 user=FokinSA";
:log info "NASOS-SSH: Если пароль не запрашивается — всё настроено верно";
