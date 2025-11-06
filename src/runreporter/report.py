from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Optional, List


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
		execution_time: Время выполнения задачи
		tasks_completed: Количество выполненных задач
		tasks_with_errors: Количество задач с ошибками
		total_errors: Общее количество ошибок
		info_messages_count: Количество информационных сообщений
		info_messages: Список информационных сообщений для краткого обзора
	"""
	run_name: Optional[str]
	had_errors: bool
	primary_channel: str
	sent_to_telegram: bool
	sent_to_email: bool
	execution_time: Optional[timedelta] = None
	tasks_completed: int = 0
	tasks_with_errors: int = 0
	total_errors: int = 0
	info_messages_count: int = 0
	info_messages: List[str] = None
	
	def __post_init__(self):
		if self.info_messages is None:
			self.info_messages = []

	def to_text(self) -> str:
		"""Базовый текст сводки без указания приоритетного канала."""
		name_part = f"Имя задачи: {self.run_name}\n" if self.run_name else ""
		status = "С ошибками" if self.had_errors else "Без ошибок"
		return f"Отчет выполнения\n{name_part}Статус: {status}\n"


def read_log_tail(log_file_path: str, max_lines: int = DEFAULT_MAX_TAIL_LINES) -> str:
	path = Path(log_file_path)
	if not path.exists():
		return "Лог-файл отсутствует."
	# Efficient tail read
	with path.open("r", encoding="utf-8", errors="ignore") as f:
		lines = f.readlines()
		return "".join(lines[-max_lines:])


def extract_info_messages(log_file_path: str, max_messages: int = 10) -> List[str]:
	"""Извлечь информационные сообщения из лога для краткого обзора.
	
	Формат лога: "2024-01-01 12:00:00 [INFO] app: [Context] message"
	
	Args:
		log_file_path: Путь к файлу лога
		max_messages: Максимальное количество сообщений для извлечения
		
	Returns:
		Список информационных сообщений
	"""
	path = Path(log_file_path)
	if not path.exists():
		return []
	
	info_messages = []
	seen_messages = set()
	
	with path.open("r", encoding="utf-8", errors="ignore") as f:
		for line in f:
			# Ищем строки с уровнем [INFO]
			if "[INFO]" in line.upper():
				# Формат: "timestamp [INFO] logger_name: message"
				# Ищем позицию после "[INFO]"
				info_pos = line.upper().find("[INFO]")
				if info_pos != -1:
					# Берем часть после "[INFO]"
					after_info = line[info_pos + 6:].strip()
					# Убираем имя логгера (до первого ":")
					if ":" in after_info:
						message = after_info.split(":", 1)[-1].strip()
					else:
						message = after_info
					
					# Добавляем только уникальные сообщения
					if message and message not in seen_messages:
						seen_messages.add(message)
						info_messages.append(message)
						if len(info_messages) >= max_messages:
							break
	
	return info_messages


def format_timedelta(td: Optional[timedelta]) -> str:
	"""Форматировать timedelta в читаемый формат.
	
	Args:
		td: Объект timedelta или None
		
	Returns:
		Строка в формате "H:MM:SS.microseconds"
	"""
	if td is None:
		return "—"
	
	total_seconds = int(td.total_seconds())
	microseconds = td.microseconds
	hours = total_seconds // 3600
	minutes = (total_seconds % 3600) // 60
	seconds = total_seconds % 60
	
	return f"{hours}:{minutes:02d}:{seconds:02d}.{microseconds:06d}"


def build_report_text(summary: RunSummary, log_tail: str, include_log_tail: bool = True) -> str:
	# Сохранено для обратной совместимости: формирует простой текст (как для email)
	return build_report_text_email(summary, log_tail, include_log_tail)


def build_report_text_email(summary: RunSummary, log_tail: str, include_log_tail: bool = True) -> str:
	"""Построить текст отчета для email."""
	parts = [
		"📊 ОТЧЕТ О ВЫПОЛНЕНИИ",
		"",
		f"⏱️ Время выполнения: {format_timedelta(summary.execution_time)}",
		"",
		f"✅ Задач выполнено: {summary.tasks_completed}",
		f"❌ Задач с ошибками: {summary.tasks_with_errors}",
		f"🚨 Всего ошибок: {summary.total_errors}",
		f"ℹ️ Информационных сообщений: {summary.info_messages_count}",
	]
	# Добавляем информацию о прикрепленном файле
	if include_log_tail:
		parts.extend([
			"",
			"📎 Подробный отчет прикреплен к сообщению.",
		])
	
	return "\n".join(parts)


def build_report_text_telegram(summary: RunSummary, log_tail: str, include_log_tail: bool = True) -> str:
	"""Построить текст отчета для Telegram с HTML-форматированием."""
	parts = [
		"<b>📊 ОТЧЕТ О ВЫПОЛНЕНИИ</b>",
		"",
		f"⏱️ <b>Время выполнения:</b> {format_timedelta(summary.execution_time)}",
		"",
		f"✅ <b>Задач выполнено:</b> {summary.tasks_completed}",
		f"❌ <b>Задач с ошибками:</b> {summary.tasks_with_errors}",
		f"🚨 <b>Всего ошибок:</b> {summary.total_errors}",
		f"ℹ️ <b>Информационных сообщений:</b> {summary.info_messages_count}",
	]
	

	# Добавляем информацию о прикрепленном файле
	if include_log_tail:
		parts.extend([
			"",
			"📎 <b>Подробный отчет прикреплен к сообщению.</b>",
		])
	
	return "\n".join(parts)


def build_log_attachment_bytes(log_tail: str) -> bytes:
	return log_tail.encode("utf-8", errors="ignore")