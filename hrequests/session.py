from functools import partial
from random import choice as rchoice
from sys import modules, stderr
from typing import Literal, Optional, Tuple, Union

import hrequests
from hrequests.headers import Headers
from hrequests.reqs import *
from hrequests.response import ProcessResponse

from .cffi import freeMemory
from .client import TLSClient
from .cookies import RequestsCookieJar
from .toolbelt import CaseInsensitiveDict


class TLSSession(TLSClient):
    """
    Session object that sends requests with TLS client.

    Args:
        browser (str): Browser to use [firefox, chrome]
        client_identifier (str): Identifier for the client
        os (Literal['win', 'mac', 'lin'], optional): OS to use in header [win, mac, lin]
        headers (dict, optional): Dictionary of HTTP headers to send with the request. Default is generated from `browser` and `os`.
        temp (bool, optional): Indicates if session is temporary. Defaults to False.
        verify (bool, optional): Verify the server's TLS certificate. Defaults to True.
        timeout (int, optional): Default timeout in seconds. Defaults to 30.
        ja3_string (str, optional): JA3 string. Defaults to None.
        h2_settings (dict, optional): HTTP/2 settings. Defaults to None.
        additional_decode (str, optional): Additional decode. Defaults to None.
        pseudo_header_order (list, optional): Pseudo header order. Defaults to None.
        priority_frames (list, optional): Priority frames. Defaults to None.
        header_order (list, optional): Header order. Defaults to None.
        force_http1 (bool, optional): Force HTTP/1. Defaults to False.
        catch_panics (bool, optional): Catch panics. Defaults to False.
        debug (bool, optional): Debug mode. Defaults to False.

    Methods:
        get(url, *, params=None, headers=None, cookies=None, allow_redirects=True, verify=None, timeout=30, proxies=None):
            Send a GET request
        post(url, *, params=None, data=None, files=None, headers=None, cookies=None, json=None, allow_redirects=True, verify=None, timeout=30, proxies=None):
            Send a POST request
        options(url, *, params=None, headers=None, cookies=None, allow_redirects=True, verify=None, timeout=30, proxies=None):
            Send a OPTIONS request
        head(url, *, params=None, headers=None, cookies=None, allow_redirects=True, verify=None, timeout=30, proxies=None):
            Send a HEAD request
        put(url, *, params=None, data=None, files=None, headers=None, cookies=None, json=None, allow_redirects=True, verify=None, timeout=30, proxies=None):
            Send a PUT request
        patch(url, *, params=None, data=None, files=None, headers=None, cookies=None, json=None, allow_redirects=True, verify=None, timeout=30, proxies=None):
            Send a PATCH request
        delete(url, *, params=None, headers=None, cookies=None, allow_redirects=True, verify=None, timeout=30, proxies=None):
            Send a DELETE request
        render(url, headless, proxy, response, mock_human):
            Render a page with playwright
    """

    def __init__(
        self,
        client_identifier: str,
        browser: Literal['firefox', 'chrome'],
        os: Optional[Literal['win', 'mac', 'lin']] = None,
        headers: Optional[dict] = None,
        temp: bool = False,
        verify: bool = True,
        timeout: float = 30,
        *args,
        **kwargs,
    ):
        super().__init__(client_identifier=client_identifier, *args, **kwargs)

        # sync network methods
        self.get: partial = partial(get, session=self)
        self.post: partial = partial(post, session=self)
        self.options: partial = partial(options, session=self)
        self.head: partial = partial(head, session=self)
        self.put: partial = partial(put, session=self)
        self.patch: partial = partial(patch, session=self)
        self.delete: partial = partial(delete, session=self)

        # async network methods
        self.async_get: partial = partial(async_get, session=self)
        self.async_post: partial = partial(async_post, session=self)
        self.async_options: partial = partial(async_options, session=self)
        self.async_head: partial = partial(async_head, session=self)
        self.async_put: partial = partial(async_put, session=self)
        self.async_patch: partial = partial(async_patch, session=self)
        self.async_delete: partial = partial(async_delete, session=self)

        # shortcut to render method
        if 'playwright' in modules:
            self.render: partial = partial(
                hrequests.browser.render, session=self, browser=self.browser
            )
        else:
            self.render: partial = partial(
                stderr.write, 'Cannot render. Playwright not installed.\n'
            )

        self.temp: bool = temp  # indicate if session is temporary
        self._closed: bool = False  # indicate if session is closed
        self.browser: str = browser  # browser name
        self._os: str = os or rchoice(('win', 'mac', 'lin'))  # os name
        self.verify: bool = verify  # default to verifying certs
        self.timeout: float = timeout  # default timeout

        # set headers
        if headers:
            self.headers = CaseInsensitiveDict(headers)
        else:
            self.resetHeaders(os=os)

    def resetHeaders(
        self,
        os: Optional[Literal['win', 'mac', 'lin']] = None,
    ):
        """
        Rotates the headers of the session
        "OS" can be one of the following:
          ['win', 'mac', 'lin']
        Default is what it was initialized with, or the last value set
        """
        if os:
            self._os = os
        self.headers = CaseInsensitiveDict(Headers(browser=self.browser, os=self._os).generate())

    @property
    def os(self) -> str:
        return self._os

    @os.setter
    def os(self, os: Literal['win', 'mac', 'lin']):
        if os not in _os_set:
            raise ValueError(f'`{os}` is not a valid OS: (win, mac, lin)')
        self.resetHeaders(os=os)

    def request(
        self,
        method: str,
        url: str,
        *,
        data: Optional[Union[str, bytes, bytearray, dict]] = None,
        files: Optional[dict] = None,
        headers: Optional[Union[dict, CaseInsensitiveDict]] = None,
        cookies: Optional[Union[RequestsCookieJar, dict, list]] = None,
        json: Optional[Union[dict, list, str]] = None,
        allow_redirects: bool = True,
        history: bool = False,
        verify: Optional[bool] = None,
        timeout: Optional[float] = None,
        proxies: Optional[dict] = None,
    ) -> 'hrequests.response.Response':
        """
        Send a request with TLS client

        Args:
            method (str): Method of request (GET, POST, OPTIONS, HEAD, PUT, PATCH, DELETE)
            url (str): URL to send request to
            data (Union[str, bytes, bytearray, dict], optional): Data to send to request. Defaults to None.
            files (dict, optional): Files to send with request. Defaults to None.
            headers (dict, optional): Dictionary of HTTP headers to send with the request. Defaults to None.
            cookies (Union[RequestsCookieJar, dict, list], optional): Dict or CookieJar to send. Defaults to None.
            json (dict, optional): Json to send in the request body. Defaults to None.
            allow_redirects (bool, optional): Allow request to redirect. Defaults to True.
            history (bool, optional): Remember request history. Defaults to False.
            verify (bool, optional): Verify the server's TLS certificate. Defaults to True.
            timeout (float, optional): Timeout in seconds. Defaults to 30.
            proxies (dict, optional): Dictionary of proxies. Defaults to None.

        Returns:
            hrequests.response.Response: Response object
        """
        proc = ProcessResponse(
            session=self,
            method=method,
            url=url,
            data=data,
            files=files,
            headers=headers,
            cookies=cookies,
            json=json,
            allow_redirects=allow_redirects,
            history=history,
            verify=self.verify if verify is None else verify,
            timeout=self.timeout if timeout is None else timeout,
            proxy=proxies,
        )
        proc.send()
        return proc.response

    def close(self):
        if not self._closed:
            self._closed = True
            freeMemory(self._session_id.encode('utf-8'))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __del__(self):
        self.close()


class Session(TLSSession):
    def __init__(
        self,
        browser: Literal['firefox', 'chrome'] = 'firefox',
        version: Optional[int] = None,
        os: Optional[Literal['win', 'mac', 'lin']] = None,
        headers: Optional[dict] = None,
        *args,
        **kwargs,
    ):
        '''
        Parameters:
            browser (Literal['firefox', 'chrome'], optional): Browser to use. Default is 'firefox'.
            version (int, optional): Version of the browser to use. Browser must be specified. Default is randomized.
            os (Literal['win', 'mac', 'lin'], optional): OS to use in header. Default is randomized.
            headers (dict, optional): Dictionary of HTTP headers to send with the request. Default is generated from `browser` and `os`.
            verify (bool, optional): Verify the server's TLS certificate. Defaults to True.
            ja3_string (str, optional): JA3 string. Defaults to None.
            h2_settings (dict, optional): HTTP/2 settings. Defaults to None.
            additional_decode (str, optional): Additional decode. Defaults to None.
            pseudo_header_order (list, optional): Pseudo header order. Defaults to None.
            priority_frames (list, optional): Priority frames. Defaults to None.
            header_order (list, optional): Header order. Defaults to None.
            force_http1 (bool, optional): Force HTTP/1. Defaults to False.
            catch_panics (bool, optional): Catch panics. Defaults to False.
            debug (bool, optional): Debug mode. Defaults to False.
        '''
        # random version if not specified
        if not version:
            version = _browsers[browser].version
        # if version is specified, check if it is supported
        elif version not in _browsers[browser].versions:
            raise ValueError(
                f'`{version}` is not a supported {browser} version: {_browsers[browser].versions}'
            )
        self.version = version

        super().__init__(
            client_identifier=f'{browser}_{version}',
            browser=browser,
            headers=headers,
            os=os,
            *args,
            **kwargs,
        )


class SessionShortcut:
    name: str
    versions: Tuple[int]

    @classmethod
    @property
    def version(cls) -> int:
        return rchoice(cls.versions)

    @classmethod
    def Session(
        cls,
        version: Optional[int] = None,
        os: Optional[Literal['win', 'mac', 'lin']] = None,
        *args,
        **kwargs,
    ) -> Session:
        return Session(
            browser=cls.name,
            version=version or cls.version,
            os=os,
            *args,
            **kwargs,
        )

    @classmethod
    def BrowserSession(
        cls,
        **kwargs,
    ):
        return hrequests.browser.BrowserSession(
            browser=cls.name,
            **kwargs,
        )


class firefox(SessionShortcut):
    name: str = 'firefox'
    versions: Tuple[int] = (102, 104, 105, 106, 108, 110)


class chrome(SessionShortcut):
    name: str = 'chrome'
    versions: Tuple[int] = (103, 104, 105, 106, 107, 108, 109, 110, 111, 112)


_browsers: dict = {'firefox': firefox, 'chrome': chrome}
_os_set: set = {'win', 'mac', 'lin'}
