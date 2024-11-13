import re
from dataclasses import dataclass
from typing import Optional

from hrequests.exceptions import ProxyFormatException


@dataclass
class Proxy:
    server: str
    username: Optional[str] = None
    password: Optional[str] = None

    proxy_reg: re.Pattern = re.compile(
        r'^(?P<schema>\w+)://'
        r'(?:'
        r'(?P<user>[^\:]+):'
        r'(?P<password>[^@]+)@)?'
        r'(?P<ip>.*?)'
        r'(?:\:'
        r'(?P<port>\d+))?$'
    )

    def __repr__(self) -> str:
        return f"<BrowserProxy {self.server}>"

    @staticmethod
    def from_url(host: str) -> 'Proxy':
        match = Proxy.proxy_reg.match(host)
        if not match:
            raise ProxyFormatException(f"Invalid proxy: {host}")
        return Proxy(
            server=f"{match['schema']}://{match['ip']}:{match['port']}",
            username=match['user'],
            password=match['password'],
        )

    def to_playwright(self) -> dict:
        if not self.username:
            return {"server": self.server}
        return {
            "server": self.server,
            "username": self.username,
            "password": self.password,
        }
