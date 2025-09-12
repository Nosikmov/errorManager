# runreporter

Библиотека для логирования ошибок и отправки отчетов по завершению выполнения.

Возможности:
- Логирование в файл
- Сбор последних 300 строк лога в отчет
- Отправка отчетов в Telegram (по chat_id)
- Отправка отчетов на Email (SMTP)
- Флаги: отправлять ли отчеты при отсутствии ошибок; приоритетный канал (Telegram/Email)

## Установка

```bash
pip install .
```

## Примеры использования

### Вариант 1: через контекстный менеджер (with)
```python
from runreporter import ErrorManager, SmtpConfig

manager = ErrorManager(
    log_file_path="app.log",
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
    primary_channel="telegram",  # "telegram" или "email"
)

with manager.context(run_name="Ежедневный импорт") as log:
    log.info("Начало работы")
    # ваш код
    log.error("Ошибка обработки записи id=42")
```

### Вариант 2: без with (явный старт и финиш)
```python
from runreporter import ErrorManager, SmtpConfig

manager = ErrorManager(
    log_file_path="app.log",
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
    # ваш код
    raise RuntimeError("Пример ошибки")
except Exception:
    log.exception("Произошло исключение")
finally:
    # В конце выполнения явно инициируем отправку отчета
    manager.send_report()  # можно передать run_name вручную: manager.send_report("Ночной job")
```

## Конфигурация
- `send_reports_without_errors`: если False, отчеты будут отправляться только при наличии ошибок
- `primary_channel`: "telegram" или "email" — приоритет канала; второй используется как резервный

## Лицензия
MIT
