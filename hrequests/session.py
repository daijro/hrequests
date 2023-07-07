from functools import partial
from random import choice as rchoice
from typing import Literal, Optional, Union

from fake_headers import Headers

import hrequests
from hrequests.reqs import *
from hrequests.response import ProcessResponse

from .cffi import freeMemory
from .client import CaseInsensitiveDict, TLSClient
from .cookies import RequestsCookieJar


class TLSSession(TLSClient):
    """
    Session object that sends requests with TLS client.

    Args:
        browser (str): Browser to use [firefox, chrome, opera]
        client_identifier (str): Identifier for the client
        os (str): OS to use in header [win, mac, lin]
        headers (dict, optional): Dictionary of HTTP headers to send with the request. Default is generated from `browser` and `os`.
        temp (bool, optional): Indicates if session is temporary. Defaults to False.
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
    
    Methods:
        get(url, *, params=None, headers=None, cookies=None, allow_redirects=True, verify=None, timeout=30, proxies=None): 
            Send a GET request
        post(url, *, params=None, data=None, headers=None, cookies=None, json=None, allow_redirects=True, verify=None, timeout=30, proxies=None): 
            Send a POST request
        options(url, *, params=None, headers=None, cookies=None, allow_redirects=True, verify=None, timeout=30, proxies=None): 
            Send a OPTIONS request
        head(url, *, params=None, headers=None, cookies=None, allow_redirects=True, verify=None, timeout=30, proxies=None): 
            Send a HEAD request
        put(url, *, params=None, data=None, headers=None, cookies=None, json=None, allow_redirects=True, verify=None, timeout=30, proxies=None): 
            Send a PUT request
        patch(url, *, params=None, data=None, headers=None, cookies=None, json=None, allow_redirects=True, verify=None, timeout=30, proxies=None): 
            Send a PATCH request
        delete(url, *, params=None, headers=None, cookies=None, allow_redirects=True, verify=None, timeout=30, proxies=None): 
            Send a DELETE request
        render(url, headless, proxy, response, mock_human): 
            Render a page with playwright
    """
    def __init__(
        self,
        browser: str,
        client_identifier: str,
        os: str,
        headers: Optional[dict] = None,
        temp: bool = False,
        verify: bool = True,
        *args,
        **kwargs
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
        self.render: partial = partial(hrequests.browser.render, session=self)

        self.temp: bool = temp  # indicate if session is temporary
        self._closed: bool = False  # indicate if session is closed
        self.browser: str = browser  # browser name
        self.os: str = os  # os name
        self.verify: bool = verify  # default to verifying certs

        # set headers
        if headers:
            self.headers = CaseInsensitiveDict(headers)
        else:
            self.resetHeaders(os=os)

    def resetHeaders(
        self,
        os: Optional[Literal['random', 'win', 'mac', 'lin']] = None,
    ):
        """
        Rotates the headers of the session
        "OS" can be one of the following:
          'random', 'win', 'mac', 'lin'
        Default is what it was initialized with, or the last value set
        """
        if os:
            self.os = os
        self.headers = Headers(browser=self.browser, os=os or self.os, headers=True).generate()

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        data: Optional[Union[str, dict]] = None,
        headers: Optional[dict] = None,
        cookies: Optional[Union[RequestsCookieJar, dict, list]] = None,
        json: Optional[Union[dict, list, str]] = None,
        allow_redirects: bool = True,
        history: bool = False,
        verify: bool = True,  # maps to insecure_skip_verify
        timeout: int = 30,  # maps to timeout_seconds
        proxies: Optional[dict] = None,
    ) -> 'hrequests.response.Response':
        """
        Send a request with TLS client

        Args:
            method (str): Method of request (GET, POST, OPTIONS, HEAD, PUT, PATCH, DELETE)
            url (str): URL to send request to
            params (dict, optional): Dictionary of URL parameters to append to the URL. Defaults to None.
            data (Union[str, dict], optional): Data to send to request. Defaults to None.
            headers (dict, optional): Dictionary of HTTP headers to send with the request. Defaults to None.
            cookies (Union[RequestsCookieJar, dict, list], optional): Dict or CookieJar to send. Defaults to None.
            json (dict, optional): Json to send in the request body. Defaults to None.
            allow_redirects (bool, optional): Allow request to redirect. Defaults to True.
            history (bool, optional): Remember request history. Defaults to False.
            verify (bool, optional): Verify the server's TLS certificate. Defaults to True.
            timeout (int, optional): Timeout in seconds. Defaults to 30.
            proxies (dict, optional): Dictionary of proxies. Defaults to None.

        Returns:
            hrequests.response.Response: Response object
        """
        if verify is None:
            verify = self.verify
        proc = ProcessResponse(
            session=self,
            method=method,
            url=url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            json=json,
            allow_redirects=allow_redirects,
            chain=history,
            insecure_skip_verify=not verify,
            timeout_seconds=timeout,
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
        browser: Literal['firefox', 'chrome', 'opera'] = 'firefox',
        client_identifier: Optional[str] = None,
        os: Literal['random', 'win', 'mac', 'lin'] = 'random',
        headers: Optional[dict] = None,
        *args,
        **kwargs
    ):
        super().__init__(
            client_identifier=client_identifier or firefox.tls,
            browser=browser,
            headers=headers,
            os=os,
            *args,
            **kwargs
        )


class SessionShortcut:
    name: str
    tls_clients: tuple
    
    @classmethod
    @property
    def tls(cls) -> str:
        return rchoice(cls.tls_clients)
    
    @classmethod
    def Session(cls, os='random', *args, **kwargs) -> Session:
        return Session(
            browser=cls.name, client_identifier=cls.tls, os=os, *args, **kwargs
        )


class firefox(SessionShortcut):
    name: str = 'firefox'
    tls_clients: tuple = ('firefox_102', 'firefox_104', 'firefox108', 'firefox110')


class chrome(SessionShortcut):
    name: str = 'chrome'
    tls_clients: tuple = (
        'chrome_103',
        'chrome_104',
        'chrome_105',
        'chrome_106',
        'chrome_107',
        'chrome_108',
        'chrome109',
        'chrome110',
        'chrome111',
        'chrome112',
    )


class opera(SessionShortcut):
    name: str = 'opera'
    tls_clients: tuple = ('opera_89', 'opera_90')
