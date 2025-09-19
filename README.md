# runreporter

Библиотека для логирования ошибок и отправки отчетов по завершению выполнения.

Возможности:
- Логирование в файл (папка для `.log` создается автоматически)
- Сбор последних 300 строк лога в отчет
- Отправка отчетов в Telegram (по chat_id)
- Отправка отчетов на Email (SMTP)
- Флаги: отправлять ли отчеты при отсутствии ошибок; приоритетный канал (Telegram/Email)

## Установка

```bash
pip install runreporter
```

## Примеры использования

### Вариант 1: через контекстный менеджер (with)
```python
from runreporter import ErrorManager, SmtpConfig

manager = ErrorManager(
    log_file_path="logs/app.log",  # папка logs будет создана автоматически
    telegram_bot_token="123:ABC",
    telegram_chat_ids=[11111111, 22222222],
    smtp_config=SmtpConfig(
        host="smtp.example.com",
        port=465,
        username="user@example.com",
        password="pass",
        use_ssl=True,
        from_addr="user@example.com",
    ),
    email_recipients=["dev1@example.com", "dev2@example.com"],
    send_reports_without_errors=False,
    primary_channel="telegram",
)

with manager.context(run_name="Ежедневный импорт") as log:
    log.info("Начало работы")
    log.error("Ошибка обработки записи id=42")
```

### Вариант 2: без with (явный старт и финиш)
```python
from runreporter import ErrorManager, SmtpConfig

manager = ErrorManager(
    log_file_path="logs/app.log",
    telegram_bot_token="123:ABC",
    telegram_chat_ids=[11111111],
    smtp_config=SmtpConfig(
        host="smtp.example.com",
        port=465,
        username="user@example.com",
        password="pass",
        use_ssl=True,
    ),
    email_recipients=["dev@example.com"],
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
from runreporter import ErrorManager
manager = ErrorManager(log_file_path="logs/app.log")

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
from runreporter import ErrorManager
manager = ErrorManager(log_file_path="logs/app.log")

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

## Конфигурация
- `send_reports_without_errors`: если False, отчеты будут отправляться только при наличии ошибок
- `primary_channel`: "telegram" или "email" — приоритет канала; второй используется как резервный

## Лицензия
MIT
