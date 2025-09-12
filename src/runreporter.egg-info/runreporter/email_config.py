from dataclasses import dataclass
from typing import Optional


@dataclass
class SmtpConfig:
	host: str
	port: int
	username: str
	password: str
	use_ssl: bool = True
	from_addr: Optional[str] = None
	use_starttls: bool = False