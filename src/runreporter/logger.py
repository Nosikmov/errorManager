import logging
from contextlib import contextmanager
from typing import List, Optional
from logging import Logger
from pathlib import Path


_GLOBAL_LOGGER: Optional["ErrorTrackingLogger"] = None


class ErrorTrackingLogger:
	"""Обертка над Python logger с отслеживанием ошибок и контекстными метками.
	
	Автоматически отслеживает наличие ошибок в логах и поддерживает стек контекстов
	для пометки сообщений префиксами вида [Context1 > Context2].
	"""

	def __init__(self, logger: Logger) -> None:
		"""Инициализация логгера с отслеживанием ошибок.
		
		Args:
			logger: Базовый Python logger для записи сообщений
		"""
		self._logger = logger
		self._had_error = False
		self._context_stack: List[str] = []

	def _mark_error(self) -> None:
		self._had_error = True

	@property
	def had_error(self) -> bool:
		"""Проверить, были ли зафиксированы ошибки в логах.
		
		Returns:
			bool: True если были ошибки, False иначе
		"""
		return self._had_error

	def _with_ctx(self, msg: str) -> str:
		if not self._context_stack:
			return msg
		ctx = " > ".join(self._context_stack)
		return f"[{ctx}] {msg}"

	def debug(self, msg: str, *args, **kwargs) -> None:
		self._logger.debug(self._with_ctx(msg), *args, **kwargs)

	def info(self, msg: str, *args, **kwargs) -> None:
		self._logger.info(self._with_ctx(msg), *args, **kwargs)

	def warning(self, msg: str, *args, **kwargs) -> None:
		self._logger.warning(self._with_ctx(msg), *args, **kwargs)

	def error(self, msg: str, *args, **kwargs) -> None:
		self._mark_error()
		self._logger.error(self._with_ctx(msg), *args, **kwargs)

	def exception(self, msg: str, *args, exc_info: bool = True, **kwargs) -> None:
		self._mark_error()
		self._logger.error(self._with_ctx(msg), *args, exc_info=exc_info, **kwargs)

	def critical(self, msg: str, *args, **kwargs) -> None:
		self._mark_error()
		self._logger.critical(self._with_ctx(msg), *args, **kwargs)

	@contextmanager
	def context(self, name: str):
		"""Контекстный менеджер для пометки сообщений.
		
		Все сообщения внутри блока будут помечены указанным контекстом.
		Контексты могут быть вложенными.
		
		Args:
			name: Имя контекста для пометки сообщений
			
		Yields:
			ErrorTrackingLogger: Текущий логгер с активным контекстом
		"""
		self._context_stack.append(str(name))
		try:
			yield self
		finally:
			self._context_stack.pop()

	def with_permanent_context(self, context_name: str) -> "PermanentContextLogger":
		"""Создать логгер с постоянным контекстом.
		
		Все сообщения будут автоматически помечены указанным контекстом.
		
		Args:
			context_name: Имя контекста для постоянной пометки сообщений
			
		Returns:
			PermanentContextLogger: Логгер с постоянным контекстом
		"""
		return PermanentContextLogger(self, context_name)


class PermanentContextLogger:
	"""Логгер с постоянным контекстом модуля.
	
	Все сообщения автоматически помечаются указанным контекстом.
	"""

	def __init__(self, base: ErrorTrackingLogger, context_name: str) -> None:
		"""Инициализация логгера с постоянным контекстом.
		
		Args:
			base: Базовый логгер с отслеживанием ошибок
			context_name: Имя контекста для постоянной пометки
		"""
		self._base = base
		self._context = str(context_name)

	@property
	def had_error(self) -> bool:
		"""Проверить, были ли зафиксированы ошибки в базовом логгере.
		
		Returns:
			bool: True если были ошибки, False иначе
		"""
		return self._base.had_error

	def _p(self, msg: str) -> str:
		return f"[{self._context}] {msg}"

	def debug(self, msg: str, *args, **kwargs) -> None:
		self._base.debug(self._p(msg), *args, **kwargs)

	def info(self, msg: str, *args, **kwargs) -> None:
		self._base.info(self._p(msg), *args, **kwargs)

	def warning(self, msg: str, *args, **kwargs) -> None:
		self._base.warning(self._p(msg), *args, **kwargs)

	def error(self, msg: str, *args, **kwargs) -> None:
		self._base.error(self._p(msg), *args, **kwargs)

	def exception(self, msg: str, *args, **kwargs) -> None:
		self._base.exception(self._p(msg), *args, **kwargs)

	def critical(self, msg: str, *args, **kwargs) -> None:
		self._base.critical(self._p(msg), *args, **kwargs)

	@contextmanager
	def context(self, name: str):
		"""Контекстный менеджер для дополнительных контекстов.
		
		Сообщения будут помечены как [ModuleContext > AdditionalContext].
		
		Args:
			name: Имя дополнительного контекста
			
		Yields:
			PermanentContextLogger: Текущий логгер с дополнительным контекстом
		"""
		with self._base.context(f"{self._context} > {name}") as _:
			yield self


class ComponentLogger:
	"""Легковесная обертка для логгера с префиксом компонента.
	
	Все сообщения автоматически помечаются префиксом [ComponentName].
	"""

	def __init__(self, base: ErrorTrackingLogger, component_name: str) -> None:
		"""Инициализация логгера компонента.
		
		Args:
			base: Базовый логгер с отслеживанием ошибок
			component_name: Имя компонента для префикса
		"""
		self._base = base
		self._component = str(component_name)

	@property
	def had_error(self) -> bool:
		"""Проверить, были ли зафиксированы ошибки в базовом логгере.
		
		Returns:
			bool: True если были ошибки, False иначе
		"""
		return self._base.had_error

	def _p(self, msg: str) -> str:
		return f"[{self._component}] {msg}"

	def debug(self, msg: str, *args, **kwargs) -> None:
		self._base.debug(self._p(msg), *args, **kwargs)

	def info(self, msg: str, *args, **kwargs) -> None:
		self._base.info(self._p(msg), *args, **kwargs)

	def warning(self, msg: str, *args, **kwargs) -> None:
		self._base.warning(self._p(msg), *args, **kwargs)

	def error(self, msg: str, *args, **kwargs) -> None:
		self._base.error(self._p(msg), *args, **kwargs)

	def exception(self, msg: str, *args, **kwargs) -> None:
		self._base.exception(self._p(msg), *args, **kwargs)

	def critical(self, msg: str, *args, **kwargs) -> None:
		self._base.critical(self._p(msg), *args, **kwargs)

	@contextmanager
	def context(self, name: str):
		"""Контекстный менеджер для пометки сообщений компонента.
		
		Сообщения будут помечены как [Component > Context].
		
		Args:
			name: Имя контекста
			
		Yields:
			ComponentLogger: Текущий логгер с активным контекстом
		"""
		with self._base.context(f"{self._component} > {name}") as _:
			yield self


def set_global_logger(logger: ErrorTrackingLogger) -> None:
	"""Установить глобальный логгер для использования в модулях.
	
	Args:
		logger: Логгер для установки как глобальный
	"""
	global _GLOBAL_LOGGER
	_GLOBAL_LOGGER = logger


def get_global_logger() -> ErrorTrackingLogger:
	"""Получить глобальный логгер.
	
	Returns:
		ErrorTrackingLogger: Глобальный логгер
		
	Raises:
		RuntimeError: Если глобальный логгер не установлен
	"""
	if _GLOBAL_LOGGER is None:
		raise RuntimeError("Global logger is not set. Initialize ErrorManager first or call set_global_logger().")
	return _GLOBAL_LOGGER


def get_logger_for(component_name: str) -> ComponentLogger:
	"""Получить логгер для компонента с префиксом.
	
	Args:
		component_name: Имя компонента для префикса
		
	Returns:
		ComponentLogger: Логгер с префиксом компонента
	"""
	return get_global_logger().with_component(component_name)


def create_file_logger(name: str, log_file_path: str, level: int = logging.INFO) -> ErrorTrackingLogger:
	# Ensure log directory exists
	path = Path(log_file_path)
	if path.parent and not path.parent.exists():
		path.parent.mkdir(parents=True, exist_ok=True)

	logger = logging.getLogger(name)
	logger.setLevel(level)
	logger.propagate = False

	# Avoid duplicate handlers if called multiple times
	if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == str(path) for h in logger.handlers):
		file_handler = logging.FileHandler(str(path), encoding="utf-8")
		formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
		file_handler.setFormatter(formatter)
		logger.addHandler(file_handler)

	return ErrorTrackingLogger(logger)