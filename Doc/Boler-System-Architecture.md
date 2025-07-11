# Система мониторинга уровня Boler - Техническая документация

**Дата создания:** 28 июня 2025  
**Автор:** Фокин Сергей Александрович  
**Проект:** NasosRunner - расширение Boler  

---

## 🎯 Общая концепция системы

Двухроутерная система управления насосом с независимым контролем уровня воды и аварийной защитой:

- **Nasos Router** - исполнительная система (управление насосом)
- **Boler Router** - система мониторинга (контроль уровня воды)

---

## 🏗️ Архитектура роутера Boler (система мониторинга)

### Аппаратная конфигурация
- **2 поплавковых датчика с герконами:**
  - Рабочий уровень (верхний)
  - Аварийный/критический уровень (нижний)
- **Кабельная линия:** 30 метров до роутера
- **LED индикатор:** на POE шине того же интерфейса
- **Возможность:** использование независимых портов для датчиков и LED

### Принцип работы датчиков
```
Геркон ЗАМКНУТ   → Тест кабеля = КЗ        → Уровень НЕ достигнут
Геркон РАЗОМКНУТ → Тест кабеля = Обрыв     → Уровень ДОСТИГНУТ
```

---

## 📋 Модульная структура Boler

### Основные модули
1. **`Boler-Init.rsc`**
   - Инициализация системы и настройка всех глобальных переменных
   - Конфигурация портов и начальных состояний
   - Проверка системы и зависимостей

2. **`Boler-Messages.rsc`**
   - Кодированные сообщения и константы состояний
   - Функции форматирования и логирования
   - Заготовки для будущих уведомлений (Telegram, Email)

3. **`Boler-LevelSensor.rsc`**
   - Мониторинг датчиков уровня
   - Тестирование кабельной линии
   - Анализ результатов (КЗ/Обрыв)
   - Формирование флагов достоверности

4. **`Boler-NetworkAPI.rsc`**
   - Связь с роутером Nasos через RouterOS API
   - Запрос состояния насоса
   - Передача данных об уровне
   - Контроль связи

5. **`Boler-StatusDisplay.rsc`**
   - Управление LED индикацией
   - Отображение состояния насоса
   - Аварийное моргание при потере связи
   - POE управление

6. **`Boler-Runner.rsc`**
   - Основной цикл координации
   - Вызов всех модулей по расписанию
   - Обработка логики взаимодействия

7. **`Boler-Startup.rsc`**
   - Автозапуск системы при старте роутера
   - Вызов Boler-Init для инициализации
   - Запуск основного цикла Runner

8. **`Boler-TimeUtils.rsc`**
   - Утилиты работы со временем
   - Адаптация из модуля Nasos-TimeUtils

---

## 🔧 Глобальные переменные Boler

### Состояние датчиков
```
BolerWorkLevelStatus     - рабочий уровень (true=достигнут, false=не достигнут)
BolerCriticalLevelStatus - аварийный уровень (true=достигнут, false=не достигнут)
BolerSensorReliable      - достоверность данных (true=данные корректны)
BolerLastSensorUpdate    - время последнего обновления датчиков
```

### Сетевое взаимодействие
```
BolerNasosConnection     - статус связи с Nasos (true=связь есть)
BolerNasosStatus         - состояние насоса с Nasos (получаемое)
BolerLastNasosUpdate     - время последнего обновления от Nasos
```

### Конфигурация
```
BolerNasosIP            - IP адрес роутера Nasos
BolerNasosUser          - имя пользователя для подключения
BolerNasosPassword      - пароль для подключения
BolerSensorPort         - порт для подключения датчиков
BolerLEDPort            - порт для LED индикации
BolerSensorInterval     - интервал опроса датчиков (сек)
BolerNetworkInterval    - интервал опроса Nasos (сек)
```

---

## 🔄 Алгоритм работы системы Boler

### 1. Инициализация (Boler-Startup → Boler-Init)
1. Boler-Startup вызывает Boler-Init для полной инициализации
2. Boler-Init устанавливает все глобальные переменные
3. Конфигурация портов (датчики, LED)
4. Проверка наличия необходимых модулей
5. Запуск основного цикла Boler-Runner

### 2. Основной цикл (Boler-Runner)
```
ЦИКЛ каждые N секунд:
  1. Вызов Boler-LevelSensor    (опрос датчиков)
  2. Вызов Boler-NetworkAPI     (связь с Nasos)
  3. Вызов Boler-StatusDisplay  (управление LED)
  4. Пауза до следующего цикла
```

### 3. Мониторинг датчиков (Boler-LevelSensor)
```
ДЛЯ КАЖДОГО датчика:
  1. Запуск теста кабеля на порту
  2. Анализ результата:
     - КЗ → уровень НЕ достигнут
     - Обрыв → уровень ДОСТИГНУТ
     - Ошибка → флаг недостоверности
  3. Сравнение с предыдущим состоянием
  4. При изменении → запись в лог
  5. Обновление глобальных переменных
```

### 4. Сетевое взаимодействие (Boler-NetworkAPI)
```
ПОПЫТКА подключения к Nasos:
  ЕСЛИ связь установлена:
    1. Запрос состояния насоса
    2. Передача данных о датчиках
    3. Обновление BolerNasosConnection=true
    4. Сохранение состояния насоса
  ИНАЧЕ:
    1. BolerNasosConnection=false
    2. Логирование потери связи
```

### 5. Управление индикацией (Boler-StatusDisplay)
```
ЕСЛИ BolerNasosConnection=true:
  LED отображает состояние насоса:
  - Постоянно → насос работает
  - Выключен → насос остановлен
  - Медленное мигание → ожидание
ИНАЧЕ:
  Аварийное быстрое моргание LED
```

---

## 🚨 Аварийная логика

### Приоритеты обработки
1. **Критический уровень** - наивысший приоритет
2. **Потеря связи с Nasos** - средний приоритет  
3. **Сбой датчиков** - контролируемая ситуация

### Обработка аварийных ситуаций
```
ЕСЛИ BolerCriticalLevelStatus=true:
  1. Немедленное уведомление Nasos (если связь есть)
  2. Аварийная индикация LED
  3. Запись критического события в лог

ЕСЛИ потеря связи с Nasos > 5 минут:
  1. Переход в автономный режим
  2. Аварийная индикация
  3. Продолжение мониторинга датчиков

ЕСЛИ сбой датчиков (BolerSensorReliable=false):
  1. Индикация неисправности
  2. Попытки восстановления
  3. Уведомление через лог
```

---

## 📡 Протокол связи между роутерами

### Выбранный протокол: RouterOS API (TCP)
- **Порт:** 8728 (обычный) / 8729 (SSL)
- **Аутентификация:** логин/пароль
- **Преимущества:** 
  - Встроенная поддержка в RouterOS
  - Прямой доступ к переменным
  - Минимальные задержки
  - Высокая надежность

### Команды обмена данными
```
Boler → Nasos:
  /system/script/environment/print where name="NasosStatus"
  
Nasos → Boler:  
  /system/script/environment/print where name="BolerWorkLevelStatus"
```

---

## 📝 Логирование событий

### Типы событий для записи
- Изменение состояния рабочего уровня
- Изменение состояния критического уровня  
- Потеря/восстановление связи с Nasos
- Сбои датчиков/восстановление
- Критические аварийные ситуации

### Формат записи лога
```
[TIMESTAMP] BOLER: [LEVEL] Событие - детали
Пример: [28.06.2025 12:30:15] BOLER: CRITICAL Аварийный уровень достигнут
```

---

## 🔧 Настройки и конфигурация

### Настраиваемые параметры
- IP адреса и учетные данные Nasos
- Интервалы опроса (датчики, сеть)
- Порты для датчиков и LED
- Пороги и таймауты
- Режимы индикации

### Файлы конфигурации
Все настройки хранятся в глобальных переменных RouterOS для обеспечения персистентности между перезагрузками.

---

## 🚀 План реализации

### Этап 1: Базовая функциональность
1. Boler-Messages.rsc - структура данных
2. Boler-LevelSensor.rsc - мониторинг датчиков
3. Boler-StatusDisplay.rsc - базовая индикация
4. Boler-Startup.rsc - инициализация

### Этап 2: Сетевое взаимодействие  
1. Boler-NetworkAPI.rsc - связь с Nasos
2. Интеграция с основным циклом
3. Обработка аварийных ситуаций

### Этап 3: Полная интеграция
1. Boler-Runner.rsc - координация всех модулей
2. Тестирование полного цикла
3. Оптимизация и отладка

---

**Документ готов к началу реализации системы Boler!** 