class ClientException(IOError):
    '''Error with the TLS client'''


class BrowserException(Exception):
    '''Base exceptions for render instances'''


class EnableMockHumanException(BrowserException):
    '''Exception raised when mock human is disabled, but captcha is called'''


class BrowserTimeoutException(BrowserException):
    '''Exception raised when playwright throws a timeout error'''


class NotRenderedException(Exception):
    '''Raise when the user tries to interact with an element that is not in a BrowserSession'''


class JavascriptException(BrowserException):
    '''Exception raised when a javascript error occurs'''


class CacheDisabledError(BrowserException):
    '''Tried to go back when cache was disabled'''


class SelectorNotFoundException(Exception):
    '''Exception raised when a css selector is not found'''


class ProxyFormatException(ClientException):
    '''Exception raised when a proxy format is not supported'''


class MissingLibraryException(ClientException):
    '''Exception raised when the browsing libraries are not installed'''
