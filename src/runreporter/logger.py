import logging
from contextlib import contextmanager
from typing import List, Optional
from logging import Logger
from pathlib import Path


_GLOBAL_LOGGER: Optional["ErrorTrackingLogger"] = None


class ErrorTrackingLogger:
	"""Wrapper around Python logger to track if any error/exception was logged.
	Поддерживает стек контекстов для пометки сообщений."""

	def __init__(self, logger: Logger) -> None:
		self._logger = logger
		self._had_error = False
		self._context_stack: List[str] = []

	def _mark_error(self) -> None:
		self._had_error = True

	@property
	def had_error(self) -> bool:
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
		self._context_stack.append(str(name))
		try:
			yield self
		finally:
			self._context_stack.pop()

	def with_component(self, name: str) -> "ComponentLogger":
		return ComponentLogger(self, name)


class ComponentLogger:
	"""Lightweight facade that prefixes all messages with a component name."""

	def __init__(self, base: ErrorTrackingLogger, component_name: str) -> None:
		self._base = base
		self._component = str(component_name)

	@property
	def had_error(self) -> bool:
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
		with self._base.context(f"{self._component} > {name}") as _:
			yield self


def set_global_logger(logger: ErrorTrackingLogger) -> None:
	global _GLOBAL_LOGGER
	_GLOBAL_LOGGER = logger


def get_global_logger() -> ErrorTrackingLogger:
	if _GLOBAL_LOGGER is None:
		raise RuntimeError("Global logger is not set. Initialize ErrorManager first or call set_global_logger().")
	return _GLOBAL_LOGGER


def get_logger_for(component_name: str) -> ComponentLogger:
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