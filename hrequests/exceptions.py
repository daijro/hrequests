class ClientException(IOError):
    """Error with the TLS client"""


class BrowserException(Exception):
    """Base exceptions for render instances"""


class EnableMockHumanException(BrowserException):
    """Exception raised when mock human is disabled, but captcha is called"""


class BrowserTimeoutException(BrowserException):
    """Exception raised when playwright throws a timeout error"""


class NoPauseRuntimeException(RuntimeError):
    """Exception raised when a request with no_pause=True is called from a different thread than it was created in"""
