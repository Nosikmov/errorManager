from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


DEFAULT_MAX_TAIL_LINES = 300


@dataclass
class RunSummary:
	"""Сводка о выполнении задачи для отчета.
	
	Attributes:
		run_name: Имя задачи
		had_errors: Были ли ошибки во время выполнения
		primary_channel: Приоритетный канал отправки
		sent_to_telegram: Отправлен ли отчет в Telegram
		sent_to_email: Отправлен ли отчет на email
	"""
	run_name: Optional[str]
	had_errors: bool
	primary_channel: str
	sent_to_telegram: bool
	sent_to_email: bool

	def to_text(self) -> str:
		"""Преобразовать сводку в текстовый формат для отчета.
		
		Returns:
			str: Текстовое представление сводки
		"""
		name_part = f"Имя задачи: {self.run_name}\n" if self.run_name else ""
		status = "С ошибками" if self.had_errors else "Без ошибок"
		primary = f"Приоритетный канал: {self.primary_channel}\n"
		channels = f"Отправлено: Telegram={self.sent_to_telegram}, Email={self.sent_to_email}\n"
		return f"Отчет выполнения\n{name_part}Статус: {status}\n{primary}{channels}"


def read_log_tail(log_file_path: str, max_lines: int = DEFAULT_MAX_TAIL_LINES) -> str:
	path = Path(log_file_path)
	if not path.exists():
		return "Лог-файл отсутствует."
	# Efficient tail read
	with path.open("r", encoding="utf-8", errors="ignore") as f:
		lines = f.readlines()
		return "".join(lines[-max_lines:])


def build_report_text(summary: RunSummary, log_tail: str) -> str:
	return (
		f"{summary.to_text()}\n"
		"Последние строки лога (до 300):\n"
		"-------------------------------\n"
		f"{log_tail}"
	)


def build_log_attachment_bytes(log_tail: str) -> bytes:
	return log_tail.encode("utf-8", errors="ignore")