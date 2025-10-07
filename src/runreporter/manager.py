from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterable, Optional, Tuple

from .email_config import SmtpConfig, NotificationUser
from .logger import ErrorTrackingLogger, create_file_logger, set_global_logger
from .report import RunSummary, read_log_tail, build_report_text, build_log_attachment_bytes
from .transports import TelegramTransport, EmailTransport


PRIMARY_TELEGRAM = "telegram"
PRIMARY_EMAIL = "email"


class ErrorManager:
	"""Основной класс для управления логированием и отправкой отчетов.
	
	Создает файловый логгер, настраивает транспорты (Telegram/Email) и предоставляет
	методы для контекстного логирования и отправки отчетов по завершению работы.
	"""
	
	def __init__(
		self,
		log_file_path: str,
		telegram_bot_token: Optional[str] = None,
		users: Optional[Iterable[NotificationUser]] = None,
		smtp_config: Optional[SmtpConfig] = None,
		send_reports_without_errors: bool = False,
		primary_channel: str = PRIMARY_TELEGRAM,
		logger_name: str = "app",
		log_level: int = logging.INFO,
	) -> None:
		"""Инициализация менеджера ошибок.
		
		Args:
			log_file_path: Путь к файлу лога (папка создается автоматически)
			telegram_bot_token: Токен бота Telegram для отправки отчетов
			users: Список пользователей для получения уведомлений
			smtp_config: Конфигурация SMTP для отправки email
			send_reports_without_errors: Отправлять ли отчеты при отсутствии ошибок
			primary_channel: Приоритетный канал ("telegram" или "email")
			logger_name: Имя логгера в записях лога
			log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
		"""
		self.log_file_path = log_file_path
		self.logger = create_file_logger(logger_name, log_file_path, level=log_level)
		set_global_logger(self.logger)
		self.tg = TelegramTransport(telegram_bot_token, users)
		self.mail = EmailTransport(smtp_config, users)
		self.send_reports_without_errors = send_reports_without_errors
		self.primary_channel = primary_channel.lower()
		self._active_run_name: Optional[str] = None

	def get_logger(self, run_name: Optional[str] = None) -> ErrorTrackingLogger:
		"""Получить логгер для записи сообщений.
		
		Args:
			run_name: Имя текущего запуска (используется в отчетах)
			
		Returns:
			ErrorTrackingLogger: Логгер с отслеживанием ошибок
		"""
		self._active_run_name = run_name
		return self.logger

	@contextmanager
	def error_context(self, name: str):
		"""Контекстный менеджер для пометки сообщений лога.
		
		Все сообщения внутри блока будут помечены указанным контекстом.
		
		Args:
			name: Имя контекста для пометки сообщений
			
		Yields:
			ErrorTrackingLogger: Логгер с активным контекстом
		"""
		with self.logger.context(name) as _:
			yield self.logger

	def send_report(self, run_name: Optional[str] = None) -> Tuple[bool, bool]:
		"""Отправить отчет о выполнении.
		
		Создает отчет с последними 300 строками лога и отправляет через настроенные
		транспорты (Telegram/Email) согласно приоритету каналов.
		
		Args:
			run_name: Имя запуска для отчета (если None, используется активное)
			
		Returns:
			Tuple[bool, bool]: (отправлено_в_telegram, отправлено_на_email)
		"""
		try:
			if self.logger.had_error or self.send_reports_without_errors:
				return self._send_report(run_name=run_name or self._active_run_name)
			return (False, False)
		except Exception as report_exc:
			logging.getLogger("runreporter.internal").error(f"Ошибка отправки отчета: {report_exc}")
			return (False, False)

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
		"""Контекстный менеджер для автоматической отправки отчета.
		
		При выходе из контекста автоматически отправляет отчет, если были ошибки
		или включена отправка отчетов без ошибок.
		
		Args:
			run_name: Имя запуска для отчета
			
		Yields:
			ErrorTrackingLogger: Логгер для записи сообщений
		"""
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
				logging.getLogger("runreporter.internal").error(f"Ошибка отправки отчета: {report_exc}")