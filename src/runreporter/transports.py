from __future__ import annotations

import json
import smtplib
import ssl
from email.message import EmailMessage
from typing import Iterable, List, Optional

import requests

from .email_config import SmtpConfig, NotificationUser


class TelegramTransport:
	"""Транспорт для отправки отчетов через Telegram Bot API."""
	
	def __init__(self, bot_token: Optional[str], users: Optional[Iterable[NotificationUser]]) -> None:
		"""Инициализация Telegram транспорта.
		
		Args:
			bot_token: Токен бота Telegram
			users: Список пользователей с настройками Telegram
		"""
		self.bot_token = bot_token
		self.users = list(users) if users else []

	@property
	def enabled(self) -> bool:
		"""Проверить, настроен ли транспорт для отправки.
		
		Returns:
			bool: True если есть токен и пользователи с Telegram, False иначе
		"""
		return bool(self.bot_token and any(user.telegram_chat_id for user in self.users))

	def send_text(self, text: str) -> List[requests.Response]:
		"""Отправить текстовое сообщение всем пользователям с Telegram.
		
		Args:
			text: Текст сообщения
			
		Returns:
			List[requests.Response]: Список ответов от Telegram API
		"""
		if not self.enabled:
			return []
		url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
		responses = []
		for user in self.users:
			if user.telegram_chat_id:
				payload = {"chat_id": user.telegram_chat_id, "text": text, "parse_mode": "HTML"}
				responses.append(requests.post(url, json=payload, timeout=20))
		return responses

	def send_document(self, caption: str, filename: str, content_bytes: bytes) -> List[requests.Response]:
		"""Отправить документ всем пользователям с Telegram.
		
		Args:
			caption: Подпись к документу
			filename: Имя файла
			content_bytes: Содержимое файла в байтах
			
		Returns:
			List[requests.Response]: Список ответов от Telegram API
		"""
		if not self.enabled:
			return []
		url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
		responses = []
		for user in self.users:
			if user.telegram_chat_id:
				files = {"document": (filename, content_bytes)}
				data = {"chat_id": str(user.telegram_chat_id), "caption": caption, "parse_mode": "HTML"}
				responses.append(requests.post(url, data=data, files=files, timeout=30))
		return responses


class EmailTransport:
	"""Транспорт для отправки отчетов через SMTP."""
	
	def __init__(self, smtp_config: Optional[SmtpConfig], users: Optional[Iterable[NotificationUser]]) -> None:
		"""Инициализация Email транспорта.
		
		Args:
			smtp_config: Конфигурация SMTP сервера
			users: Список пользователей с настройками email
		"""
		self.smtp_config = smtp_config
		self.users = list(users) if users else []

	@property
	def enabled(self) -> bool:
		"""Проверить, настроен ли транспорт для отправки.
		
		Returns:
			bool: True если есть конфигурация и пользователи с email, False иначе
		"""
		return bool(self.smtp_config and any(user.email for user in self.users))

	def _connect(self) -> smtplib.SMTP:
		assert self.smtp_config is not None
		if self.smtp_config.use_ssl:
			context = ssl.create_default_context()
			server = smtplib.SMTP_SSL(self.smtp_config.host, self.smtp_config.port, context=context, timeout=30)
		else:
			server = smtplib.SMTP(self.smtp_config.host, self.smtp_config.port, timeout=30)
		if self.smtp_config.use_starttls and not self.smtp_config.use_ssl:
			server.starttls(context=ssl.create_default_context())
		server.login(self.smtp_config.username, self.smtp_config.password)
		return server

	def send(self, subject: str, body: str, attachments: Optional[List[tuple[str, bytes, str]]] = None) -> None:
		"""Отправить email всем пользователям с email адресами.
		
		Args:
			subject: Тема письма
			body: Текст письма
			attachments: Список вложений (filename, content_bytes, mime_type)
		"""
		if not self.enabled:
			return
		assert self.smtp_config is not None

		msg = EmailMessage()
		from_addr = self.smtp_config.from_addr or self.smtp_config.username
		msg["From"] = from_addr
		
		# Собираем всех пользователей с email
		email_recipients = [user.email for user in self.users if user.email]
		msg["To"] = ", ".join(email_recipients)
		msg["Subject"] = subject
		msg.set_content(body)

		for attachment in attachments or []:
			filename, content, mime_type = attachment
			maintype, subtype = mime_type.split("/", 1)
			msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

		with self._connect() as server:
			server.send_message(msg)