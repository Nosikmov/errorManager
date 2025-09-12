from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterable, Optional, Tuple

from .email_config import SmtpConfig
from .logger import ErrorTrackingLogger, create_file_logger
from .report import RunSummary, read_log_tail, build_report_text, build_log_attachment_bytes
from .transports import TelegramTransport, EmailTransport


PRIMARY_TELEGRAM = "telegram"
PRIMARY_EMAIL = "email"


class ErrorManager:
	def __init__(
		self,
		log_file_path: str,
		telegram_bot_token: Optional[str] = None,
		telegram_chat_ids: Optional[Iterable[int]] = None,
		smtp_config: Optional[SmtpConfig] = None,
		email_recipients: Optional[Iterable[str]] = None,
		send_reports_without_errors: bool = False,
		primary_channel: str = PRIMARY_TELEGRAM,
		logger_name: str = "error_manager",
		log_level: int = logging.INFO,
	) -> None:
		self.log_file_path = log_file_path
		self.logger = create_file_logger(logger_name, log_file_path, level=log_level)
		self.tg = TelegramTransport(telegram_bot_token, telegram_chat_ids)
		self.mail = EmailTransport(smtp_config, email_recipients)
		self.send_reports_without_errors = send_reports_without_errors
		self.primary_channel = primary_channel.lower()

	def _send_report(self, run_name: Optional[str]) -> Tuple[bool, bool]:
		log_tail = read_log_tail(self.log_file_path)
		summary = RunSummary(
			run_name=run_name,
			had_errors=self.logger.had_error,
			primary_channel=self.primary_channel,
			sent_to_telegram=False,
			sent_to_email=False,
		)
		text = build_report_text(summary, log_tail)
		attachment_bytes = build_log_attachment_bytes(log_tail)

		sent_tg = False
		sent_mail = False

		def try_send_telegram() -> bool:
			if not self.tg.enabled:
				return False
			self.tg.send_text(text)
			self.tg.send_document(caption="Лог последней сессии", filename="log_tail.txt", content_bytes=attachment_bytes)
			return True

		def try_send_email() -> bool:
			if not self.mail.enabled:
				return False
			self.mail.send(
				subject=f"Отчет выполнения: {run_name or ''}",
				body=text,
				attachments=[("log_tail.txt", attachment_bytes, "text/plain")],
			)
			return True

		# Priority sending
		if self.primary_channel == PRIMARY_TELEGRAM:
			sent_tg = try_send_telegram()
			sent_mail = try_send_email() if not sent_tg else try_send_email()
		elif self.primary_channel == PRIMARY_EMAIL:
			sent_mail = try_send_email()
			sent_tg = try_send_telegram() if not sent_mail else try_send_telegram()
		else:
			# fallback: attempt both
			sent_tg = try_send_telegram()
			sent_mail = try_send_email()

		return sent_tg, sent_mail

	@contextmanager
	def context(self, run_name: Optional[str] = None):
		try:
			yield self.logger
		except Exception as exc:
			self.logger.exception(f"Исключение во время выполнения: {exc}")
			raise
		finally:
			try:
				if self.logger.had_error or self.send_reports_without_errors:
					self._send_report(run_name=run_name)
			except Exception as report_exc:
				# Avoid crashing the app due to reporting issues
				logging.getLogger("error_manager.internal").error(f"Ошибка отправки отчета: {report_exc}")