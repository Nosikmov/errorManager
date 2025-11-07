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

## Быстрый старт (рекомендуется)

```python
# config.py
from runreporter import ErrorManager, SmtpConfig, NotificationUser

users = [
    NotificationUser(name="admin", telegram_chat_id=11111111, email="admin@example.com"),
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
)
app_logger = manager.get_logger(run_name="MainApp")

# любой модуль приложения
from config import app_logger
log = app_logger.with_permanent_context("Billing.Invoices")  # фиксированный контекст модуля

log.info("Start")                 # [Billing.Invoices] Start
with log.context("Worker"):
    log.error("Parse failed")     # [Billing.Invoices > Worker] Parse failed
```

> Примечание: контекст модуля задается один раз через `with_permanent_context("ModuleName")`. Для локальных шагов используйте `with log.context("Step"):`.

## Примеры использования

### Вариант 1 (опционально): через контекстный менеджер (with)

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

### Вариант 2 (опционально): без with (явный старт и финиш)
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

### Вариант 3 (опционально): локальный контекст сообщений

> В большинстве случаев удобнее использовать постоянный контекст (см. Быстрый старт). Локальный контекст полезен для кратковременных шагов внутри модуля.

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

# Дополнительно: использование по модулям

```python
# config.py - центральный файл конфигурации
from runreporter import ErrorManager, SmtpConfig, NotificationUser

manager = ErrorManager(
    log_file_path="logs/app.log",
    logger_name="myapp",
    users=[NotificationUser(name="admin", telegram_chat_id=11111111)],
)
app_logger = manager.get_logger(run_name="MainApp")

# service_orders/__init__.py (контекст модуля)
from config import app_logger
log = app_logger.with_permanent_context("Orders")

# service_orders/processor.py
from service_orders import log

log.info("Загрузка заказов")              # [Orders] ...
with log.context("Валидация"):
    log.error("Неверный статус заказа")   # [Orders > Валидация] ...

# service_reports/generator.py — другой модуль
from config import app_logger
rep_log = app_logger.with_permanent_context("Reports.Generator")
rep_log.info("Старт генерации")           # [Reports.Generator] ...
```

> Замечание: иерархические хелперы `with_permanent_context_path`, `child`, `from_module` и `get_logger_for` удалены. Используйте только `with_permanent_context("Module")` и при необходимости `with log.context("Step"):`.

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

## Уровни логирования на модуль

```python
from config import app_logger
import logging

# Модуль A — пишем только INFO и выше
logA = app_logger.with_permanent_context("ModuleA", level=logging.INFO)
logA.debug("skip")     # пропустится
logA.info("ok")        # [ModuleA] ok

# Модуль B — хотим подробный DEBUG
logB = app_logger.with_permanent_context("ModuleB", level=logging.DEBUG)
logB.debug("details")  # [ModuleB] details
logB.error("boom")     # [ModuleB] boom

# Локальный дополнительный контекст в модуле B
with logB.context("Step1"):
    logB.info("work")  # [ModuleB > Step1] work
```

> Важно: глобальный `ErrorManager(log_level=...)` задаёт минимальный уровень для всего приложения. 
> Чтобы модульные DEBUG не отбрасывались, установите `log_level=logging.DEBUG` при создании `ErrorManager`, 
> а затем ограничивайте модульные уровни через `with_permanent_context(..., level=...)`.

## Работа с асинхронными задачами (asyncio.gather)

При использовании `asyncio.gather` для параллельного выполнения нескольких задач, каждая задача должна использовать свой контекст через `with log.context("TaskName")`. 

**Важно:** Логгер использует `contextvars` для изоляции контекстов в асинхронном коде. Это означает, что каждая асинхронная задача имеет свой собственный изолированный стек контекстов, и контексты не наслаиваются друг на друга при параллельном выполнении.

Это обеспечивает:
- **Полную изоляцию контекстов** между параллельными задачами (контексты не наслаиваются)
- Автоматическое логирование исключений в каждой задаче
- Корректную статистику ошибок

**Правильный паттерн:**

```python
import asyncio
from config import manager, app_logger

async def process_file_source(get_file_func, source_name, subfolder, filename):
    """
    Универсальная функция для обработки источника файла
    
    Args:
        get_file_func: функция для получения файла
        source_name: название источника (для логирования)
        subfolder: подпапка для сохранения
        filename: имя файла
        
    Returns:
        bool: True если файл успешно обработан, False иначе
    """
    # Используем контекст для изоляции задачи
    # Исключения автоматически логируются, try/except не нужен
    with app_logger.context(source_name):
        app_logger.info(f"Начало обработки {source_name}")
        
        # Получаем файл
        file_data = await get_file_func()
        
        # Обработка файла...
        app_logger.info(f"Файл {source_name} успешно обработан")
        return True

async def main():
    file_sources = [
        {'func': get_file_1, 'name': 'Priceva API', 'subfolder': 'priceva', 'filename': 'data.json'},
        {'func': get_file_2, 'name': 'External API', 'subfolder': 'external', 'filename': 'data.json'},
    ]
    
    # Основной контекст оборачивает весь gather
    # Отчет будет отправлен автоматически после завершения всех задач
    with manager.context(run_name="Импорт данных"):
        tasks = []
        task_names = []
        
        for source in file_sources:
            tasks.append(
                process_file_source(
                    source['func'],
                    source['name'],
                    source['subfolder'],
                    source['filename']
                )
            )
            task_names.append(source['name'])
        
        # Выполняем все задачи параллельно
        # return_exceptions=True гарантирует, что исключения не прервут выполнение
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты (опционально)
        for name, result in zip(task_names, results):
            if isinstance(result, Exception):
                app_logger.error(f"Задача {name} завершилась с ошибкой: {result}")
            elif result:
                app_logger.info(f"Задача {name} выполнена успешно")

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
```

**Ключевые моменты:**

1. **Основной контекст** (`with manager.context()`) оборачивает весь `gather` — это обеспечивает единое время выполнения и отправку отчета после завершения всех задач.

2. **Контекст задачи** (`with app_logger.context(source_name)`) внутри каждой асинхронной функции изолирует логи этой задачи. Благодаря использованию `contextvars`, каждая параллельная задача имеет свой собственный стек контекстов, поэтому контексты не наслаиваются друг на друга.

3. **Не нужен try/except** в функциях — контекстный менеджер автоматически перехватывает и логирует исключения.

4. **Статистика собирается корректно** — все ошибки из всех задач учитываются в общем отчете.

**Пример вывода логов (контексты изолированы):**

```
2025-11-07 09:59:39,485 [INFO] OptLoader: [Priceva API] Начало обработки Priceva API
2025-11-07 09:59:39,486 [INFO] OptLoader: [External API] Начало обработки External API
2025-11-07 09:59:39,487 [INFO] OptLoader: [Priceva API] Файл получен
2025-11-07 09:59:39,488 [INFO] OptLoader: [External API] Файл получен
```

Каждая задача имеет свой изолированный контекст, контексты не смешиваются.

**Пример с постоянным контекстом модуля:**

Если вы используете постоянный контекст модуля (`with_permanent_context`), он будет работать вместе с контекстами задач:

```python
# config.py
from config import app_logger

# Создаем логгер с постоянным контекстом модуля
log = app_logger.with_permanent_context("FileProcessor")

async def process_file_source(get_file_func, source_name, subfolder, filename):
    # Контекст задачи добавляется к постоянному контексту модуля
    with log.context(source_name):
        log.info(f"Начало обработки {source_name}")
        # Вывод: [FileProcessor > Priceva API] Начало обработки Priceva API
        
        file_data = await get_file_func()
        log.info(f"Файл получен")
        # Вывод: [FileProcessor > Priceva API] Файл получен
        return True
```

**Пример с обработкой ошибок:**

```python
async def process_file_source(get_file_func, source_name, subfolder, filename):
    with app_logger.context(source_name):
        app_logger.info(f"Начало обработки {source_name}")
        
        try:
            file_data = await get_file_func()
            # Обработка...
            app_logger.info(f"Успешно обработано")
            return True
        except Exception as e:
            # Исключение уже будет залогировано контекстом,
            # но можно добавить дополнительную информацию
            app_logger.error(f"Детали ошибки: {e}")
            return False
```

> **Важно:** 
> - Контекстный менеджер `log.context()` автоматически логирует исключения, поэтому в большинстве случаев `try/except` не требуется. Используйте его только если нужна дополнительная обработка ошибок.
> - Благодаря `contextvars`, каждый async-контекст имеет свой изолированный стек контекстов, поэтому параллельные задачи не влияют друг на друга.