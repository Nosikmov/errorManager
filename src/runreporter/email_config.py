from dataclasses import dataclass
from typing import Optional


@dataclass
class SmtpConfig:
	"""Конфигурация SMTP сервера для отправки email отчетов.
	
	Attributes:
		host: Адрес SMTP сервера
		port: Порт SMTP сервера
		username: Имя пользователя для аутентификации
		password: Пароль для аутентификации
		use_ssl: Использовать SSL соединение (по умолчанию True)
		from_addr: Email адрес отправителя (если None, используется username)
		use_starttls: Использовать STARTTLS для шифрования (взаимоисключающе с use_ssl)
	"""
	host: str
	port: int
	username: str
	password: str
	use_ssl: bool = True
	from_addr: Optional[str] = None
	use_starttls: bool = False


@dataclass
class NotificationUser:
	"""Пользователь для получения уведомлений.
	
	Attributes:
		name: Имя пользователя (для идентификации в логах)
		telegram_chat_id: ID чата Telegram (если None, уведомления в Telegram не отправляются)
		email: Email адрес (если None, уведомления на email не отправляются)
	"""
	name: str
	telegram_chat_id: Optional[int] = None
	email: Optional[str] = None