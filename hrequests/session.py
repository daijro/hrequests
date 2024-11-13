from functools import partial
from random import choice as rchoice
from typing import Dict, Literal, Optional, Tuple, Union

from browserforge.headers import Browser as BFConstraints
from browserforge.headers import HeaderGenerator
from ua_parser import user_agent_parser

import hrequests
from hrequests.proxies import BaseProxy
from hrequests.reqs import *
from hrequests.response import ProcessResponse

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
        get(url, *, params=None, headers=None, cookies=None, allow_redirects=True, verify=None, timeout=30, proxy=None):
            Send a GET request
        post(url, *, params=None, data=None, files=None, headers=None, cookies=None, json=None, allow_redirects=True, verify=None, timeout=30, proxy=None):
            Send a POST request
        options(url, *, params=None, headers=None, cookies=None, allow_redirects=True, verify=None, timeout=30, proxy=None):
            Send a OPTIONS request
        head(url, *, params=None, headers=None, cookies=None, allow_redirects=True, verify=None, timeout=30, proxy=None):
            Send a HEAD request
        put(url, *, params=None, data=None, files=None, headers=None, cookies=None, json=None, allow_redirects=True, verify=None, timeout=30, proxy=None):
            Send a PUT request
        patch(url, *, params=None, data=None, files=None, headers=None, cookies=None, json=None, allow_redirects=True, verify=None, timeout=30, proxy=None):
            Send a PATCH request
        delete(url, *, params=None, headers=None, cookies=None, allow_redirects=True, verify=None, timeout=30, proxy=None):
            Send a DELETE request
        render(url, headless, proxy, response, mock_human):
            Render a page with playwright
    """

    def __init__(
        self,
        *,
        browser: Literal['firefox', 'chrome'],
        version: Optional[int] = None,
        os: Optional[Literal['win', 'mac', 'lin']] = None,
        headers: Optional[dict] = None,
        temp: bool = False,
        verify: bool = True,
        timeout: float = 30,
        **kwargs,
    ):
        self.browser: str = browser  # browser name

        # browser version
        self.tls_version: Optional[int] = version

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

        self.temp: bool = temp  # indicate if session is temporary
        self._os: Literal['win', 'mac', 'lin'] = os or rchoice(('win', 'mac', 'lin'))  # os name
        self.verify: bool = verify  # default to verifying certs
        self.timeout: float = timeout  # default timeout

        # set headers
        if headers:
            self._headers = CaseInsensitiveDict(headers)
            self.version = version or get_major_version(headers)
        else:
            self.resetHeaders(os=os)
            assert self.version

        super().__init__(client_identifier=f'{browser}_{self.tls_version}', **kwargs)

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
        self.headers = CaseInsensitiveDict(
            generate_headers(self.browser, version=self.tls_version, os=OS_MAP[os or self._os])
        )

    @property
    def headers(self) -> CaseInsensitiveDict:
        return self._headers

    @headers.setter
    def headers(self, headers: Union[dict, CaseInsensitiveDict]) -> None:
        # print the line of the caller and the file
        if isinstance(headers, dict):
            headers = CaseInsensitiveDict(headers)

        self._headers = headers
        # Update the major version
        self.version = get_major_version(headers)

    @property
    def os(self) -> str:
        return self._os

    @os.setter
    def os(self, os: Literal['win', 'mac', 'lin']):
        if os not in OS_MAP:
            raise ValueError(f'`{os}` is not a valid OS: (win, mac, lin)')
        self.resetHeaders(os=os)

    def render(self, url: str, proxy: Optional[Union[str, BaseProxy]] = None, *args, **kwargs):
        """Shortcut to render method"""
        return hrequests.browser.render(
            url,
            *args,
            **kwargs,
            os=self._os,
            session=self,
            version=self.version,
            browser=self.browser,
            proxy=proxy or self.proxy,
        )

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
        proxy: Optional[Union[str, BaseProxy]] = None,
        process: bool = True,
    ) -> Union['hrequests.response.Response', 'hrequests.response.ProcessResponse']:
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
            proxy (Union[str, BaseProxy], optional): Proxy URL. Defaults to None.

        Returns:
            hrequests.response.Response: Response object
        """
        # convert BaseProxy to host string
        if isinstance(proxy, BaseProxy):
            proxy = str(proxy)

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
            proxy=proxy,
        )
        if not process:
            # return an unfinished ProcessResponse object
            return proc
        proc.send()
        return proc.response


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
            version (int, optional): The version of the browser's TLS to use.
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
        # if version is specified, check if it is supported
        if version and version not in BROWSER_MAP[browser].versions:
            raise ValueError(
                f'`{version}` is not a supported {browser} version: {BROWSER_MAP[browser].versions}'
            )
        if version:
            version = BROWSER_MAP[browser].tls_version(version)
        else:
            # default to the latest tls
            version = BROWSER_MAP[browser].versions[-1]

        super().__init__(
            browser=browser,
            version=version,
            headers=headers,
            os=os,
            *args,
            **kwargs,
        )


class SessionShortcut:
    name: Literal['firefox', 'chrome']
    versions: Tuple[int, ...]

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
            version=version,
            os=os,
            *args,
            **kwargs,
        )

    @classmethod
    def tls_version(cls, version: int) -> int:
        # Find the minimum corresponding TLS version
        for v in cls.versions[::-1]:
            if version >= v:
                return v
        raise ValueError(f'No supported TLS version found for {cls.name.title()}: {version}')

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
    name: Literal['firefox'] = 'firefox'
    versions: Tuple[int, ...] = (102, 104, 105, 106, 108, 110, 117, 120, 123)


class chrome(SessionShortcut):
    name: Literal['chrome'] = 'chrome'
    versions: Tuple[int, ...] = (103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 117, 120, 124)


BROWSER_MAP = {'firefox': firefox, 'chrome': chrome}
OS_MAP = {'win': 'windows', 'mac': 'macos', 'lin': 'linux'}


_hg = HeaderGenerator()


def generate_headers(name: str, version: Optional[int] = None, **kwargs) -> Dict[str, str]:
    """
    Generate headers for a browser

    Args:
        name (str): Browser name
        version (int, optional): Browser version. If specified, the max supported version
            in the TLS versioning range is used.
        kwargs: Additional keyword arguments to pass to `HeaderGenerator.generate`

    Returns:
        Tuple[Dict[str, str], int]: Headers and major version
    """
    browser: Union[str, BFConstraints]
    if version:
        # Find the max supported version in the TLS versioning range
        browser = BFConstraints(name=name, min_version=version)
    else:
        browser = name
    return _hg.generate(browser=(browser,), **kwargs)


def get_major_version(headers: Union[Dict[str, str], CaseInsensitiveDict]) -> Optional[int]:
    # Get the major version
    if 'User-Agent' not in headers:
        return None
    major_version = user_agent_parser.ParseUserAgent(headers['User-Agent']).get('major')
    return int(major_version) if major_version else None
