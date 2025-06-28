# ════════════════════════════════════════════════════════════════
# ИНСТРУКЦИЯ ПО НАСТРОЙКЕ SSH МЕЖДУ ROUTEROS
# ════════════════════════════════════════════════════════════════
# 
# Настройка автоматического SSH-соединения между роутерами
# Nasos (главный) и Boler (дочерний) для опроса датчиков уровня воды
#
# Автор: NasosRunner Project
# Версия: 1.0
# ════════════════════════════════════════════════════════════════

## 📋 ОБЩАЯ СХЕМА НАСТРОЙКИ

```
┌─────────────────┐    SSH-ключи    ┌─────────────────┐
│                 │◄────────────────►│                 │
│   NASOS         │                  │   BOLER         │
│   (10.10.55.1)  │                  │   (10.10.55.2)  │
│                 │                  │                 │
│   SSH-клиент    │                  │   SSH-сервер    │
│   Генерирует    │                  │   Принимает     │
│   ключи         │                  │   ключи         │
└─────────────────┘                  └─────────────────┘
```

## 🚀 ПОШАГОВАЯ НАСТРОЙКА

### ЭТАП 1: НАСТРОЙКА НА РОУТЕРЕ NASOS (ГЛАВНЫЙ)

1. **Загрузите скрипт настройки SSH**
   ```bash
   # Загрузите файл Nasos-SSH-Setup.rsc на роутер Nasos
   # Используйте MikrotikUploader или WinBox
   ```

2. **Запустите скрипт настройки**
   ```bash
   /system script run Nasos-SSH-Setup
   ```

3. **Что произойдет:**
   - ✅ Генерация SSH-ключей RSA 2048 бит
   - ✅ Настройка SSH-клиента для подключения к Boler
   - ✅ Экспорт публичного ключа в файл
   - ✅ Тестирование соединения (покажет ошибку - это нормально)

4. **Получите файл с публичным ключом**
   ```bash
   # Файл будет создан: nasos-public-key-nasos-to-boler.txt
   # Скопируйте его на роутер Boler любым способом:
   # - WinBox (Files)
   # - FTP/SCP
   # - USB-накопитель
   ```

### ЭТАП 2: НАСТРОЙКА НА РОУТЕРЕ BOLER (ДОЧЕРНИЙ)

1. **Загрузите скрипт настройки SSH**
   ```bash
   # Загрузите файл Boler-SSH-Setup.rsc на роутер Boler
   ```

2. **Скопируйте файл с публичным ключом**
   ```bash
   # Поместите файл nasos-public-key-nasos-to-boler.txt в корень файловой системы
   # Проверьте наличие: /file print
   ```

3. **Запустите скрипт настройки**
   ```bash
   /system script run Boler-SSH-Setup
   ```

4. **Что произойдет:**
   - ✅ Импорт публичного ключа от Nasos
   - ✅ Настройка SSH-сервера
   - ✅ Добавление ключа к пользователю
   - ✅ Очистка временных файлов

### ЭТАП 3: ТЕСТИРОВАНИЕ СОЕДИНЕНИЯ

1. **Тест на роутере Nasos**
   ```bash
   /system script run Nasos-SSH-Test
   ```

2. **Тест на роутере Boler**
   ```bash
   /system script run Boler-SSH-Test
   ```

3. **Ручной тест SSH-соединения**
   ```bash
   # На роутере Nasos выполните:
   /system ssh-exec address=10.10.55.2 user=FokinSA command=":put \$BolerStatus"
   ```

## 🔧 КОМАНДЫ ДЛЯ РУЧНОЙ НАСТРОЙКИ

### На роутере NASOS:

```bash
# Генерация SSH-ключей
/ssh key generate key-name=nasos-to-boler key-type=rsa key-size=2048

# Настройка SSH-клиента
/ssh client add address=10.10.55.2 user=FokinSA key=nasos-to-boler

# Экспорт публичного ключа
/ssh key export public-key-name=nasos-to-boler
```

### На роутере BOLER:

```bash
# Импорт публичного ключа
/ssh public-key import public-key-file=nasos-public-key-nasos-to-boler.txt key-name=nasos-to-boler

# Включение SSH-сервера
/ip service set ssh disabled=no

# Добавление ключа к пользователю
/user ssh-keys import user=FokinSA public-key-file=nasos-public-key-nasos-to-boler.txt
```

## 🚨 УСТРАНЕНИЕ ПРОБЛЕМ

### Проблема: "SSH-соединение не работает"

**Возможные причины:**
1. SSH-сервер отключен на Boler
2. Публичный ключ не импортирован
3. Пользователь не имеет SSH-ключей
4. Проблемы с файрволом

**Решение:**
```bash
# На Boler проверьте:
/ip service print where name=ssh
/ssh public-key print
/user ssh-keys print
/ip firewall filter print where chain=input and dst-port=22
```

### Проблема: "Публичный ключ не найден"

**Решение:**
```bash
# Убедитесь что файл скопирован:
/file print

# Проверьте содержимое файла:
/file get nasos-public-key-nasos-to-boler.txt contents
```

### Проблема: "Пользователь не найден"

**Решение:**
```bash
# Создайте пользователя или используйте существующего:
/user add name=FokinSA group=full password=your_password
```

## 🔒 БЕЗОПАСНОСТЬ

### Рекомендуемые настройки:

1. **Ограничение доступа по IP**
   ```bash
   /ip service set ssh address=10.10.55.0/24
   ```

2. **Настройка файрвола**
   ```bash
   /ip firewall filter add chain=input protocol=tcp dst-port=22 src-address=10.10.55.1 action=accept
   /ip firewall filter add chain=input protocol=tcp dst-port=22 action=drop
   ```

3. **Отключение парольной авторизации**
   ```bash
   /ip ssh set password-auth=no
   ```

## 📊 ИНТЕГРАЦИЯ С СИСТЕМОЙ

После успешной настройки SSH:

1. **Модуль Boler-NetworkAPI.rsc** сможет опрашивать Boler через SSH
2. **Автоматический опрос** датчиков уровня воды будет работать
3. **Переменные Boler** будут доступны на роутере Nasos

### Пример использования в скриптах:

```bash
# Получение статуса датчиков
:local bolerStatus [/system ssh-exec address=10.10.55.2 user=FokinSA command=":put \$BolerStatus"]

# Получение уровня воды
:local level1 [/system ssh-exec address=10.10.55.2 user=FokinSA command=":put \$BolerLevel1"]
```

## 📝 ЛОГИ И ДИАГНОСТИКА

Все операции логируются с префиксами:
- `NASOS-SSH:` - операции на роутере Nasos
- `BOLER-SSH:` - операции на роутере Boler

Для просмотра логов:
```bash
/log print where message~"SSH"
```

## ✅ КОНТРОЛЬНЫЙ СПИСОК

- [ ] SSH-ключи сгенерированы на Nasos
- [ ] Публичный ключ экспортирован в файл
- [ ] Файл скопирован на Boler
- [ ] Публичный ключ импортирован на Boler
- [ ] SSH-сервер включен на Boler
- [ ] Пользователь настроен на Boler
- [ ] SSH-ключ добавлен к пользователю
- [ ] Тестирование прошло успешно
- [ ] Файрвол настроен (опционально)
- [ ] Система готова к работе

## 🆘 ПОДДЕРЖКА

При возникновении проблем:
1. Проверьте логи: `/log print where message~"SSH"`
2. Запустите тестовые скрипты
3. Проверьте сетевую доступность между роутерами
4. Убедитесь что все файлы загружены корректно 