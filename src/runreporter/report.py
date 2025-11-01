from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


DEFAULT_MAX_TAIL_LINES = 120


@dataclass
class RunSummary:
	"""Сводка о выполнении задачи для отчета.
	
	Attributes:
		run_name: Имя задачи
		had_errors: Были ли ошибки во время выполнения
		sent_to_telegram: Отправлен ли отчет в Telegram
		sent_to_email: Отправлен ли отчет на email
	"""
	run_name: Optional[str]
	had_errors: bool
	primary_channel: str
	sent_to_telegram: bool
	sent_to_email: bool

	def to_text(self) -> str:
		"""Базовый текст сводки без каналов доставки (для унификации формата)."""
		name_part = f"Имя задачи: {self.run_name}\n" if self.run_name else ""
		status = "С ошибками" if self.had_errors else "Без ошибок"
		return f"Отчет выполнения\n{name_part}Статус: {status}\n{primary}"


def read_log_tail(log_file_path: str, max_lines: int = DEFAULT_MAX_TAIL_LINES) -> str:
	path = Path(log_file_path)
	if not path.exists():
		return "Лог-файл отсутствует."
	# Efficient tail read
	with path.open("r", encoding="utf-8", errors="ignore") as f:
		lines = f.readlines()
		return "".join(lines[-max_lines:])


def build_report_text(summary: RunSummary, log_tail: str, include_log_tail: bool = True) -> str:
	# Сохранено для обратной совместимости: формирует простой текст (как для email)
	return build_report_text_email(summary, log_tail, include_log_tail)


def build_report_text_email(summary: RunSummary, log_tail: str, include_log_tail: bool = True) -> str:
	base = summary.to_text()
	if include_log_tail:
		return (
			f"{base}"
			"Последние строки лога (до 120):\n"
			"-------------------------------\n"
			f"{log_tail}"
		)
	return base


def build_report_text_telegram(summary: RunSummary, log_tail: str, include_log_tail: bool = True) -> str:
	# Красивое HTML-оформление для Telegram (parse_mode=HTML)
	status_text = "❌ С ошибками" if summary.had_errors else "✅ Без ошибок"
	primary_map = {"telegram": "Telegram", "email": "Email"}
	primary = primary_map.get(summary.primary_channel.lower(), summary.primary_channel)
	run_name = summary.run_name or "—"

	parts = [
		f"<b>Отчет выполнения</b>",
		f"<b>Имя задачи:</b> {run_name}",
		f"<b>Статус:</b> {status_text}",
	]
	if include_log_tail:
		parts.append("<b>Последние строки лога (до 300):</b>")
		# Оборачиваем хвост лога в <pre> для сохранения форматирования
		# Простейшее экранирование угловых скобок
		escaped = (
			log_tail.replace("&", "&amp;")
			.replace("<", "&lt;")
			.replace(">", "&gt;")
		)
		parts.append(f"<pre>{escaped}</pre>")

	return "\n".join(parts)


def build_log_attachment_bytes(log_tail: str) -> bytes:
	return log_tail.encode("utf-8", errors="ignore")