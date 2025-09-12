from __future__ import annotations

import json
import smtplib
import ssl
from email.message import EmailMessage
from typing import Iterable, List, Optional

import requests

from .email_config import SmtpConfig


class TelegramTransport:
	def __init__(self, bot_token: Optional[str], chat_ids: Optional[Iterable[int]]) -> None:
		self.bot_token = bot_token
		self.chat_ids = list(chat_ids) if chat_ids else []

	@property
	def enabled(self) -> bool:
		return bool(self.bot_token and self.chat_ids)

	def send_text(self, text: str) -> List[requests.Response]:
		if not self.enabled:
			return []
		url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
		responses = []
		for chat_id in self.chat_ids:
			payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
			responses.append(requests.post(url, json=payload, timeout=20))
		return responses

	def send_document(self, caption: str, filename: str, content_bytes: bytes) -> List[requests.Response]:
		if not self.enabled:
			return []
		url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
		responses = []
		for chat_id in self.chat_ids:
			files = {"document": (filename, content_bytes)}
			data = {"chat_id": str(chat_id), "caption": caption, "parse_mode": "HTML"}
			responses.append(requests.post(url, data=data, files=files, timeout=30))
		return responses


class EmailTransport:
	def __init__(self, smtp_config: Optional[SmtpConfig], recipients: Optional[Iterable[str]]) -> None:
		self.smtp_config = smtp_config
		self.recipients = list(recipients) if recipients else []

	@property
	def enabled(self) -> bool:
		return bool(self.smtp_config and self.recipients)

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
		if not self.enabled:
			return
		assert self.smtp_config is not None

		msg = EmailMessage()
		from_addr = self.smtp_config.from_addr or self.smtp_config.username
		msg["From"] = from_addr
		msg["To"] = ", ".join(self.recipients)
		msg["Subject"] = subject
		msg.set_content(body)

		for attachment in attachments or []:
			filename, content, mime_type = attachment
			maintype, subtype = mime_type.split("/", 1)
			msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

		with self._connect() as server:
			server.send_message(msg)