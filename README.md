# runreporter

Библиотека для логирования ошибок и отправки отчетов по завершению выполнения.

Возможности:
- Логирование в файл (папка для `.log` создается автоматически)
- Сбор последних 300 строк лога в отчет
- Отправка отчетов в Telegram (по chat_id)
- Отправка отчетов на Email (SMTP)
- Поддержка множественных пользователей с индивидуальными настройками
- Флаги: отправлять ли отчеты при отсутствии ошибок; приоритетный канал (Telegram/Email)

## Установка

```bash
pip install runreporter
```

## Примеры использования

### Вариант 1: через контекстный менеджер (with)
```python
from runreporter import ErrorManager, SmtpConfig, NotificationUser

# Создаем пользователей с индивидуальными настройками
users = [
    NotificationUser(name="admin", telegram_chat_id=11111111, email="admin@example.com"),
    NotificationUser(name="dev1", telegram_chat_id=22222222),  # только Telegram
    NotificationUser(name="dev2", email="dev2@example.com"),    # только Email
]

manager = ErrorManager(
    log_file_path="logs/app.log",  # папка logs будет создана автоматически
    logger_name="myapp",  # имя в логах (по умолчанию "app")
    telegram_bot_token="123:ABC",
    users=users,
    smtp_config=SmtpConfig(
        host="smtp.example.com",
        port=465,
        username="user@example.com",
        password="pass",
        use_ssl=True,
        from_addr="user@example.com",
    ),
    send_reports_without_errors=False,
    primary_channel="telegram",
)

with manager.context(run_name="Ежедневный импорт") as log:
    log.info("Начало работы")
    log.error("Ошибка обработки записи id=42")
```

### Вариант 2: без with (явный старт и финиш)
```python
from runreporter import ErrorManager, SmtpConfig, NotificationUser

users = [
    NotificationUser(name="admin", telegram_chat_id=11111111, email="admin@example.com"),
    NotificationUser(name="dev", email="dev@example.com"),
]

manager = ErrorManager(
    log_file_path="logs/app.log",
    logger_name="myapp",  # имя в логах
    telegram_bot_token="123:ABC",
    users=users,
    smtp_config=SmtpConfig(
        host="smtp.example.com",
        port=465,
        username="user@example.com",
        password="pass",
        use_ssl=True,
    ),
    send_reports_without_errors=False,
    primary_channel="email",
)

log = manager.get_logger(run_name="Ночной job")

try:
    log.info("Старт job")
    raise RuntimeError("Пример ошибки")
except Exception:
    log.exception("Произошло исключение")
finally:
    manager.send_report()
```

### Вариант 3: локальный контекст сообщений
```python
log = manager.get_logger(run_name="ETL")

log.info("Подготовка")
with manager.error_context("Загрузка CSV"):
    log.info("Читаю файл")
    log.error("Ошибка парсинга")  # [ETL > Загрузка CSV] ...
log.info("Финиш")
```

### Вариант 4: централизованная конфигурация с постоянными контекстами модулей
```python
# config.py - центральный файл конфигурации
from runreporter import ErrorManager, SmtpConfig, NotificationUser

users = [
    NotificationUser(name="admin", telegram_chat_id=11111111, email="admin@example.com"),
    NotificationUser(name="dev1", telegram_chat_id=22222222),
]

manager = ErrorManager(
    log_file_path="logs/app.log",
    logger_name="myapp",
    telegram_bot_token="123:ABC",
    users=users,
    smtp_config=SmtpConfig(
        host="smtp.example.com",
        port=465,
        username="user@example.com",
        password="pass",
        use_ssl=True,
    ),
    send_reports_without_errors=False,
    primary_channel="telegram",
)

# Экспортируем настроенный логгер для использования в модулях
app_logger = manager.get_logger(run_name="MainApp")

# service_a.py - модуль A
from config import app_logger

# Создаем логгер с постоянным контекстом модуля
log = app_logger.with_permanent_context("ServiceA")

def process_data():
    log.info("Начало обработки данных")  # [ServiceA] Начало обработки данных
    log.error("Ошибка валидации")        # [ServiceA] Ошибка валидации
    
    # Можно добавить дополнительный контекст
    with log.context("Валидация"):
        log.info("Проверка данных")      # [ServiceA > Валидация] Проверка данных

# service_b.py - модуль B  
from config import app_logger

# Создаем логгер с постоянным контекстом модуля
log = app_logger.with_permanent_context("ServiceB")

def send_notification():
    log.info("Отправка уведомления")     # [ServiceB] Отправка уведомления
    log.warning("Медленный ответ API")   # [ServiceB] Медленный ответ API

# main.py - основной файл
from config import app_logger
from service_a import process_data
from service_b import send_notification

with app_logger.context("Запуск приложения"):
    app_logger.info("Старт системы")
    process_data()
    send_notification()
    app_logger.info("Завершение работы")
```

### Вариант 5: внедрение зависимостей (DI) с постоянными контекстами
```python
# config.py - центральный файл конфигурации
from runreporter import ErrorManager, SmtpConfig, NotificationUser

users = [NotificationUser(name="admin", telegram_chat_id=11111111)]
manager = ErrorManager(log_file_path="logs/app.log", logger_name="myapp", users=users)

# Экспортируем настроенный логгер
app_logger = manager.get_logger(run_name="MainApp")

# mymodule.py - модуль с DI
from config import app_logger

class Worker:
    def __init__(self) -> None:
        # Создаем логгер с постоянным контекстом класса
        self.log = app_logger.with_permanent_context("Worker")

    def run(self) -> None:
        self.log.info("Старт работы")  # [Worker] Старт работы
        with self.log.context("Обработка данных"):
            self.log.info("Читаю файл")    # [Worker > Обработка данных] Читаю файл
            self.log.error("Ошибка парсинга")  # [Worker > Обработка данных] Ошибка парсинга

# main.py - основной файл
from config import app_logger
from mymodule import Worker

worker = Worker()

with app_logger.context("Запуск приложения"):
    app_logger.info("Инициализация системы")
    worker.run()
    app_logger.info("Завершение работы")
```

## Конфигурация пользователей

Каждый пользователь может иметь:
- **Только Telegram**: `NotificationUser(name="user", telegram_chat_id=123456)`
- **Только Email**: `NotificationUser(name="user", email="user@example.com")`
- **Оба канала**: `NotificationUser(name="user", telegram_chat_id=123456, email="user@example.com")`

## Приоритет отправки

- `primary_channel`: "telegram" или "email" — приоритетный канал
- Если приоритетный канал недоступен, используется резервный
- Каждый пользователь получает уведомления по своим настроенным каналам

## Лицензия
MIT