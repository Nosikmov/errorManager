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

### Вариант 4: общий логгер из разных модулей (без передачи экземпляра)
```python
# main.py
from runreporter import ErrorManager, NotificationUser
users = [NotificationUser(name="admin", telegram_chat_id=11111111)]
manager = ErrorManager(log_file_path="logs/app.log", logger_name="myapp", users=users)

# service_a.py
from runreporter import get_logger_for
log = get_logger_for("ServiceA")
log.info("Запуск")  # [ServiceA] ...

# service_b.py
from runreporter import get_logger_for
log = get_logger_for("ServiceB")
log.error("Ошибка")  # [ServiceB] ...
```

### Вариант 5: общий логгер через внедрение зависимостей (DI)
```python
# main.py
from runreporter import ErrorManager, NotificationUser
users = [NotificationUser(name="admin", telegram_chat_id=11111111)]
manager = ErrorManager(log_file_path="logs/app.log", logger_name="myapp", users=users)

from runreporter import get_logger_for
from mymodule import Worker

worker = Worker(get_logger_for("Worker"))
worker.run()

# mymodule.py
from runreporter import ComponentLogger

class Worker:
    def __init__(self, log: ComponentLogger) -> None:
        self.log = log

    def run(self) -> None:
        self.log.info("Старт")
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