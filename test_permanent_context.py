#!/usr/bin/env python3
"""
Тест для проверки функции with_permanent_context
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from runreporter import ErrorManager, NotificationUser

# Создаем тестовый менеджер
manager = ErrorManager(
    log_file_path="test.log",
    logger_name="test",
    users=[NotificationUser(name="test", telegram_chat_id=123456)]
)

# Получаем логгер
app_logger = manager.get_logger(run_name="TestApp")

# Проверяем, что метод with_permanent_context существует
print("Проверяем наличие метода with_permanent_context...")
if hasattr(app_logger, 'with_permanent_context'):
    print("✅ Метод with_permanent_context найден!")
    
    # Создаем логгер с постоянным контекстом
    module_logger = app_logger.with_permanent_context("TestModule")
    print("✅ Логгер с постоянным контекстом создан!")
    
    # Проверяем, что это PermanentContextLogger
    from runreporter import PermanentContextLogger
    if isinstance(module_logger, PermanentContextLogger):
        print("✅ Тип PermanentContextLogger корректен!")
        
        # Тестируем логирование
        module_logger.info("Тестовое сообщение")
        print("✅ Логирование работает!")
        
        # Проверяем дополнительный контекст
        with module_logger.context("Дополнительный контекст"):
            module_logger.info("Сообщение с дополнительным контекстом")
        print("✅ Дополнительный контекст работает!")
        
    else:
        print("❌ Неправильный тип логгера!")
else:
    print("❌ Метод with_permanent_context не найден!")

print("\nТест завершен!")
