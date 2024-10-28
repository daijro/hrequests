import os
from abc import ABC


class BaseProxy(ABC):
    def __init__(self, **kwargs):
        self.kwargs = {name: self._from_env(value) for name, value in kwargs.items()}

    def __repr__(self):
        return f"<{self.SERVICE} ({self.kwargs['username']})>"

    @staticmethod
    def _from_env(value: str) -> str:
        """
        Check the string is in the env,
        If not, use the string
        """
        return os.getenv(value) or value

    def __str__(self):
        return self.URL.format(**self.kwargs)
