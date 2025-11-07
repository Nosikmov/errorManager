import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import List, Optional
from logging import Logger
from pathlib import Path


_GLOBAL_LOGGER: Optional["ErrorTrackingLogger"] = None

# ContextVar для изоляции стека контекстов в асинхронном коде
_context_stack_var: ContextVar[List[str]] = ContextVar("_context_stack", default=[])


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
		self._info_count = 0
		self._error_count = 0
		self._warning_count = 0
	
	def _get_context_stack(self) -> List[str]:
		"""Получить стек контекстов для текущего async контекста."""
		return _context_stack_var.get()
	
	def _set_context_stack(self, stack: List[str]) -> None:
		"""Установить стек контекстов для текущего async контекста."""
		_context_stack_var.set(stack)

	def _mark_error(self) -> None:
		self._had_error = True

	@property
	def had_error(self) -> bool:
		"""Проверить, были ли зафиксированы ошибки в логах.
		
		Returns:
			bool: True если были ошибки, False иначе
		"""
		return self._had_error

	def reset_error_flag(self) -> None:
		"""Сбросить флаг наличия ошибок перед новым запуском."""
		self._had_error = False
		self._info_count = 0
		self._error_count = 0
		self._warning_count = 0
	
	@property
	def info_count(self) -> int:
		"""Количество информационных сообщений."""
		return self._info_count
	
	@property
	def error_count(self) -> int:
		"""Количество сообщений об ошибках."""
		return self._error_count
	
	@property
	def warning_count(self) -> int:
		"""Количество предупреждений."""
		return self._warning_count

	def _with_ctx(self, msg: str) -> str:
		context_stack = self._get_context_stack()
		if not context_stack:
			return msg
		ctx = " > ".join(context_stack)
		return f"[{ctx}] {msg}"

	def debug(self, msg: str, *args, **kwargs) -> None:
		self._logger.debug(self._with_ctx(msg), *args, **kwargs)

	def info(self, msg: str, *args, **kwargs) -> None:
		self._info_count += 1
		self._logger.info(self._with_ctx(msg), *args, **kwargs)

	def warning(self, msg: str, *args, **kwargs) -> None:
		self._warning_count += 1
		self._logger.warning(self._with_ctx(msg), *args, **kwargs)

	def error(self, msg: str, *args, **kwargs) -> None:
		self._mark_error()
		self._error_count += 1
		self._logger.error(self._with_ctx(msg), *args, **kwargs)

	def exception(self, msg: str, *args, exc_info: bool = True, **kwargs) -> None:
		self._mark_error()
		self._error_count += 1
		self._logger.error(self._with_ctx(msg), *args, exc_info=exc_info, **kwargs)

	def critical(self, msg: str, *args, **kwargs) -> None:
		self._mark_error()
		self._error_count += 1
		self._logger.critical(self._with_ctx(msg), *args, **kwargs)

	@contextmanager
	def context(self, name: str):
		"""Контекстный менеджер для пометки сообщений.
		
		Все сообщения внутри блока будут помечены указанным контекстом.
		Контексты могут быть вложенными.
		Автоматически логирует исключения, если они возникают внутри контекста.
		Использует contextvars для изоляции контекстов в асинхронном коде.
		
		Args:
			name: Имя контекста для пометки сообщений
			
		Yields:
			ErrorTrackingLogger: Текущий логгер с активным контекстом
		"""
		context_stack = self._get_context_stack()
		# Создаем копию стека для текущего async контекста
		new_stack = context_stack.copy()
		new_stack.append(str(name))
		self._set_context_stack(new_stack)
		try:
			yield self
		except Exception as exc:
			# Автоматически логируем исключение с контекстом
			self.exception(f"Исключение в контексте '{name}': {exc}")
			raise
		finally:
			# Восстанавливаем предыдущий стек
			self._set_context_stack(context_stack)

	def with_permanent_context(self, context_name: str, level: Optional[int] = None) -> "PermanentContextLogger":
		"""Создать логгер с постоянным контекстом.
		
		Args:
			context_name: Имя контекста для постоянной пометки сообщений
			level: Минимальный уровень для этого логгера (например, logging.INFO)
		"""
		logger = PermanentContextLogger(self, context_name)
		if level is not None:
			logger.set_level(level)
		return logger

	def with_permanent_context_path(self, *segments: str) -> "PermanentContextLogger":
		raise NotImplementedError("with_permanent_context_path is removed. Use with_permanent_context(name) per-module.")

	def from_module(self, module_name: str, project: Optional[str] = None) -> "PermanentContextLogger":
		raise NotImplementedError("from_module is removed. Use with_permanent_context(name) and set module name explicitly.")

		parts = [p for p in str(module_name).split(".") if p]
		if project:
			parts.insert(0, project)
		return self.with_permanent_context_path(*parts)


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
		self._min_level: Optional[int] = None

	def set_level(self, level: int) -> "PermanentContextLogger":
		"""Задать минимальный уровень логирования для данного логгера модуля.
		Например: logging.INFO или logging.DEBUG. Возвращает self для чейнинга.
		"""
		self._min_level = int(level)
		return self

	def _enabled(self, level: int) -> bool:
		if self._min_level is None:
			return True
		return int(level) >= int(self._min_level)

	@property
	def had_error(self) -> bool:
		"""Проверить, были ли зафиксированы ошибки в базовом логгере.
		
		Returns:
			bool: True если были ошибки, False иначе
		"""
		return self._base.had_error

	def _p(self, msg: str) -> str:
		return f"[{self._context}] {msg}"

	def child(self, segment: str) -> "PermanentContextLogger":
		raise NotImplementedError("child is removed. Use a separate module-level context via with_permanent_context.")

	def with_additional_context_path(self, *segments: str) -> "PermanentContextLogger":
		raise NotImplementedError("with_additional_context_path is removed. Use with(log.context(\"Step\")) inside a module.")

	def debug(self, msg: str, *args, **kwargs) -> None:
		if self._enabled(logging.DEBUG):
			self._base.debug(self._p(msg), *args, **kwargs)

	def info(self, msg: str, *args, **kwargs) -> None:
		if self._enabled(logging.INFO):
			self._base.info(self._p(msg), *args, **kwargs)

	def warning(self, msg: str, *args, **kwargs) -> None:
		if self._enabled(logging.WARNING):
			self._base.warning(self._p(msg), *args, **kwargs)

	def error(self, msg: str, *args, **kwargs) -> None:
		if self._enabled(logging.ERROR):
			self._base.error(self._p(msg), *args, **kwargs)

	def exception(self, msg: str, *args, **kwargs) -> None:
		# exception соотносится с ERROR
		if self._enabled(logging.ERROR):
			self._base.exception(self._p(msg), *args, **kwargs)

	def critical(self, msg: str, *args, **kwargs) -> None:
		if self._enabled(logging.CRITICAL):
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


def get_logger_for(component_name: str):
	raise NotImplementedError("get_logger_for is removed. Import logger from config and call with_permanent_context(name).")


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