import asyncio
from http.client import responses as status_codes
from random import randint
from typing import Any, Callable, Dict, List, Literal, Optional, Pattern, Union

import hrequests
from hrequests.browser.proxy import Proxy
from hrequests.client import CaseInsensitiveDict
from hrequests.cookies import RequestsCookieJar, cookiejar_to_list, list_to_cookiejar
from hrequests.exceptions import CacheDisabledError, JavascriptException
from hrequests.proxies import BaseProxy
from hrequests.response import Response
from hrequests.session import OS_MAP

from .common import ERROR, browser_client
from .engine import BrowserEngine, BrowserObjectWrapper


class BrowserSession:
    """
    Args:
        session (hrequests.session.TLSSession, optional): Session to use for headers, cookies, etc.
        resp (hrequests.response.Response, optional): Response to update with cookies, headers, etc.
        proxy (Union[str, BaseProxy], optional): Proxy to use for the browser. Example: http://1.2.3.4:8080
        mock_human (bool, optional): Whether to emulate human behavior. Defaults to False.
        engine (BrowserEngine, optional): Pass in an existing BrowserEngine instead of creating a new one
        verify (bool, optional): Whether to verify https requests
        os (Literal['win', 'mac', 'lin'], optional): Generate headers for a specific OS
        **kwargs: Additional arguments to pass to Camoufox (see https://camoufox.com/python/usage)

    Attributes:
        url (str): Get the page url
        headers (dict): Get the browser headers (User-Agent)
        content (str): Get the current page content
        cookies (RequestsCookieJar): Get the browser cookies
        status_code (int): Status code of the last response
        reason (Optional[str]): Gets the official W3C name for the status code

    Navigation Methods:
        goto(url): Navigate to a URL.
        forward(): Navigate to the next page in history
        back(): Navigate to the previous page in history
        awaitNavigation(): Wait for the page navigation to finish
        awaitScript(script, arg): Wait for a script to return true
        awaitSelector(selector, arg): Wait for a selector to exist
        awaitEnabled(selector, arg): Wait for a selector to be enabled
        isVisible(selector): Check if a selector is visible
        isEnabled(selector): Check if a selector is enabled
        awaitUrl(url, timeout): Wait for the URL to match
        dragTo(source, target, timeout, wait_after, check): Drag and drop a selector
        type(selector, text, delay, timeout): Type text into a selector
        click(selector, click_count, button, timeout, wait_after): Click a selector
        hover(selector, modifiers, timeout): Hover over a selector
        evaluate(script, arg): Evaluate and return a script
        screenshot(selector, path, full_page): Take a screenshot of the page
        setHeaders(headers): Set the browser headers. Note that this will NOT update the TLSSession headers
        close(): Close the instance

    Network Methods:
        get(url, params, headers, timeout, verify, max_redirects): Send a GET request
        post(url, params, headers, data, form, multipart, timeout, verify, max_redirects): Send a POST request
        put(url, params, headers, data, form, multipart, timeout, verify, max_redirects): Send a PUT request
        patch(url, params, headers, data, form, multipart, timeout, verify, max_redirects): Send a PATCH request
        delete(url, params, headers, timeout, verify, max_redirects): Send a DELETE request
        head(url, params, headers, timeout, verify, max_redirects): Send a HEAD request
    """

    def __init__(
        self,
        *,
        session: Optional[hrequests.session.TLSSession] = None,
        resp: Optional[hrequests.response.Response] = None,
        proxy: Optional[Union[str, BaseProxy]] = None,
        mock_human: bool = False,
        extensions: Optional[List[str]] = None,
        os: Optional[Literal['win', 'mac', 'lin']] = None,
        engine: Optional['BrowserEngine'] = None,
        browser: Literal['firefox', 'chrome'] = 'firefox',
        verify: bool = True,
        **launch_options,
    ) -> None:
        # Remember session and resp to clone cookies back to when closing
        self.session: Optional[hrequests.session.TLSSession] = session
        self.resp: Optional[hrequests.response.Response] = resp
        self.browser: Literal['firefox', 'chrome'] = browser

        # Set the engine, or create one if not provided
        if engine:
            self.engine = engine
            self.temp_engine = False
        else:
            self.engine = BrowserEngine(browser_type=browser)
            self.temp_engine = True

        if isinstance(proxy, BaseProxy):
            proxy = str(proxy)

        self.proxy: Optional[Proxy] = Proxy.from_url(proxy) if proxy else None
        self.verify: bool = verify
        self.os: Literal['win', 'mac', 'lin'] = os
        self._headers: Optional[dict] = None

        # Browser config
        self.status_code: Optional[int]
        if self.resp is not None:
            self.status_code = self.resp.status_code
        else:
            self.status_code = None

        # Bool to indicate browser is running
        self._closed: bool = False

        # Launch options
        self.launch_options: dict = launch_options
        if extensions:
            self.launch_options['addons'] = extensions

        # Handle mock_human
        self.mock_human: bool = mock_human
        self.launch_options['humanize'] = mock_human
        # Use cache by default
        self.launch_options['enable_cache'] = self.launch_options.get('enable_cache', True)

        # Start the browser
        self.start()

    def start(self) -> None:
        asyncio.run(self.__start())

    async def __start(self) -> None:
        # Build the playwright instance
        self.client = await browser_client(
            browser_type=self.browser,
            engine=self.engine,
            proxy=self.proxy.to_playwright() if self.proxy else None,
            verify=self.verify,
            os=OS_MAP[self.os] if self.os else None,
            **self.launch_options,
        )
        # Create a new page
        self.page = self.client.new_page()
        # Save the context
        self.context = self.client.context

    def shutdown(self) -> None:
        self._closed = True

        self.client.stop()

        if self.temp_engine:
            self.engine.stop()

    def __enter__(self) -> 'BrowserSession':
        return self

    def __exit__(self, *_) -> None:
        self.close()

    """
    Common public functions
    """

    def goto(self, url):
        '''Navigate to a URL'''
        resp = self.page.goto(url)
        self.status_code = resp.status
        return resp

    def forward(self):
        '''Navigate to the next page in history'''
        if self.browser == 'firefox' and not self.launch_options['enable_cache']:
            raise CacheDisabledError('When `enable_cache` is False, you cannot go back or forward.')

        return self.page.go_forward()

    def back(self):
        '''Navigate to the previous page in history'''
        if self.browser == 'firefox' and not self.launch_options['enable_cache']:
            raise CacheDisabledError('When `enable_cache` is False, you cannot go back or forward.')

        return self.page.go_back()

    def awaitNavigation(self, timeout: float = 30):
        '''
        Wait for the page navigation to finish

        Parameters:
            timeout (float, optional): Timeout in seconds. Defaults to 30.
        '''
        return self.page.wait_for_load_state(timeout=int(timeout * 1e3))

    def awaitScript(self, script: str, arg: Optional[str] = None, *, timeout: float = 30):
        '''
        Wait for a script to return true

        Parameters:
            script (str): Script to evaluate
            arg (str, optional): Argument to pass to script
            timeout (float, optional): Timeout in seconds. Defaults to 30.
        '''
        return self.page.wait_for_function(script, arg=arg, timeout=int(timeout * 1e3))

    def awaitSelector(self, selector, *, timeout: float = 30):
        '''
        Wait for a selector to exist

        Parameters:
            selector (str): Selector to wait for
            timeout (float, optional): Timeout in seconds. Defaults to 30.
        '''
        self.page.wait_for_function(
            "selector => !!document.querySelector(selector)",
            arg=selector,
            timeout=int(timeout * 1e3),
        )

    def awaitEnabled(self, selector, *, timeout: float = 30):
        '''
        Wait for a selector to be enabled

        Parameters:
            selector (str): Selector to wait for
            timeout (float, optional): Timeout in seconds. Defaults to 30.
        '''
        self.page.wait_for_function(
            "selector => !document.querySelector(selector).disabled",
            arg=selector,
            timeout=int(timeout * 1e3),
        )

    def isVisible(self, selector: str) -> bool:
        '''
        Check if a selector is visible

        Parameters:
            selector (str): Selector to check
        '''
        return self.page.is_visible(selector)

    def isEnabled(self, selector: str) -> bool:
        '''
        Check if a selector is enabled

        Parameters:
            selector (str): Selector to check
        '''
        if not self.page.is_visible(selector):
            return False
        return self.page.evaluate(
            "selector => !document.querySelector(selector).disabled", arg=selector
        )

    def awaitUrl(
        self, url: Union[str, Pattern[str], Callable[[str], bool]], *, timeout: float = 30
    ):
        '''
        Wait for the url to match a string, regex, or a python function to return True

        Parameters:
            url (Union[str, Pattern[str], Callable[[str], bool]]) - URL to match for
            timeout (float, optional): Timeout in seconds. Defaults to 30.
        '''
        return self.page.wait_for_url(url, timeout=int(timeout * 1e3))

    def dragTo(
        self,
        source: str,  # selector to drag on
        target: str,  # selector to drop on
        *,
        timeout: float = 30,  # timeout in seconds
        wait_after: bool = False,  # dont wait for a page event
        check: bool = False,  # check if element is able to be dragged
    ):
        '''
        Drag and drop a selector

        Parameters:
            source (str): Source to drag from
            target (str): Target to drop to
            timeout (float, optional): Timeout in seconds. Defaults to 30.
            wait_after (bool, optional): Wait for a page event before continuing. Defaults to False.
            check (bool, optional): Check if an element is draggable before running. Defaults to False.
        '''
        return self.page.drag_and_drop(
            source, target, no_wait_after=not wait_after, timeout=int(timeout * 1e3), check=check
        )

    def type(self, selector: str, text: str, delay: int = 50, *, timeout: float = 30):
        '''
        Type text into a selector

        Parameters:
            selector (str): CSS selector to type in
            text (str): Text to type
            delay (int, optional): Delay between keypresses in ms. On mock_human, this is randomized by 50%. Defaults to 50.
            timeout (float, optional): Timeout in seconds. Defaults to 30.
        '''
        if not self.mock_human:
            return self.page.type(selector, text, delay=delay, timeout=int(timeout * 1e3))

        for char in text:
            # Randomly enter characters with a 50% MOE
            self.page.keyboard.type(
                char, delay=randint(int(delay * 0.5), int(delay * 1.5))  # nosec
            )

    def click(
        self,
        selector: str,
        button: Optional[Literal['left', 'right', 'middle']] = 'left',
        count: int = 1,
        *,
        timeout: float = 30,
        wait_after: bool = True,
    ):
        '''
        Click a selector

        Parameters:
            selector (str): CSS selector to click
            button (Literal['left', 'right', 'middle'], optional): Button to click. Defaults to 'left'.
            count (int, optional): Number of clicks. Defaults to 1.
            timeout (float, optional): Timeout in seconds. Defaults to 30.
            wait_after (bool, optional): Wait for a page event before continuing. Defaults to True.
        '''
        return self.page.click(
            selector,
            button=button,
            click_count=count,
            timeout=int(timeout * 1e3),
            no_wait_after=not wait_after,
        )

    def hover(
        self,
        selector: str,
        modifiers: Optional[List[Literal['Alt', 'Control', 'Meta', 'Shift']]] = None,
        *,
        timeout: float = 90,
    ):
        '''
        Hover over a selector

        Parameters:
            selector (str): CSS selector to hover over
            modifiers (List[Literal['Alt', 'Control', 'Meta', 'Shift']], optional): Modifier keys to press. Defaults to None.
            timeout (float, optional): Timeout in seconds. Defaults to 90.
        '''
        return self.page.hover(selector, modifiers=modifiers, timeout=int(timeout * 1e3))

    def evaluate(self, script: str, arg: Optional[str] = None):
        '''
        Evaluate and return javascript

        Parameters:
            script (str): Javascript to evaluate in the page
            arg (str, optional): Argument to pass into the javascript function
        '''
        try:
            return self.page.evaluate(script, arg=arg)
        except ERROR as e:
            raise JavascriptException('Javascript eval exception') from e

    def screenshot(
        self, selector: Optional[str] = None, path: Optional[str] = None, *, full_page: bool = False
    ) -> Optional[bytes]:
        '''
        Take a screenshot of the page

        Parameters:
            selector (str, optional): CSS selector to screenshot
            path (str, optional): Path to save screenshot to. Defaults to None.
            full_page (bool): Whether to take a screenshot of the full scrollable page. Cannot be used with selector. Defaults to False.

        Returns:
            Optional[bytes]: Returns the screenshot buffer, if `path` was not provided
        '''
        assert bool(selector) ^ full_page, 'Must provide either `selector` or `full_page`'
        if selector:
            locator: BrowserObjectWrapper = BrowserObjectWrapper(
                self.page.locator(selector), self.engine
            )
            buffer = locator.screenshot(path=path)
        else:
            buffer = self.page.screenshot(path=path, full_page=full_page)
        if not path:  # dont return buffer if path was provided
            return buffer
        return None  # Make mypy happy

    '''
    .url, .content, .cookies, .html, properties
    makes this compatible with TLSSession
    '''

    def getContent(self):
        '''Get the page content'''
        return self.page.content()

    def getCookies(self) -> RequestsCookieJar:
        '''Get the page cookies'''
        browser_cookies: list = self.context.cookies()
        return list_to_cookiejar(browser_cookies)

    @property
    def url(self) -> str:
        '''Get the page url'''
        return self.page.url

    @url.setter
    def url(self, url: str):
        '''Go to page url'''
        self.goto(url)

    @property
    def headers(self) -> CaseInsensitiveDict:
        '''Get the page headers'''
        if self._headers:
            return CaseInsensitiveDict(self._headers)

        # Extract User-Agent
        ua = self.evaluate('navigator.userAgent')
        return CaseInsensitiveDict({'User-Agent': ua})

    @headers.setter
    def headers(self, headers: Union[dict, CaseInsensitiveDict]):
        '''Set headers'''
        self.setHeaders(headers)

    @property
    def content(self) -> str:
        '''Get the page url'''
        return self.getContent()

    @property
    def proxies(self):
        return {'all': self.proxy} if self.proxy else {}

    @proxies.setter
    def proxies(self, _: dict):
        raise NotImplementedError('Cannot set proxies on a browser session')

    @property
    def cookies(self) -> RequestsCookieJar:
        '''Get the context cookies'''
        return self.getCookies()

    @cookies.setter
    def cookies(self, cookiejar: RequestsCookieJar):
        '''Set the context cookies'''
        self.setCookies(cookiejar)

    @property
    def html(self) -> 'hrequests.parser.HTML':
        '''Get the page html as an HTML object'''
        return hrequests.parser.HTML(session=self, url=self.url, html=self.content)

    @property
    def text(self) -> str:
        '''Get the page text'''
        return self.getContent()

    @property
    def find(self) -> Callable:
        return self.html.find

    @property
    def find_all(self) -> Callable:
        return self.html.find_all

    @property
    def reason(self) -> Optional[str]:
        if self.status_code is not None:
            return status_codes[self.status_code]

    '''
    Network request functions
    '''

    def request(
        self,
        method: Literal['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD'],
        url: str,
        *,
        params: Optional[Dict[str, Union[str, float, bool]]] = None,
        data: Optional[Union[Any, str, bytes]] = None,
        headers: Optional[Union[Dict[str, str], CaseInsensitiveDict]] = None,
        form: Optional[Dict[str, Union[str, float, bool]]] = None,
        multipart: Optional[Dict[str, Union[bytes, bool, float, str]]] = None,
        timeout: float = 30,
        verify: bool = True,
        max_redirects: Optional[int] = None,
    ) -> Response:
        '''
        Parameters:
            method (Literal['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD']): HTTP method to use
            url (str): URL to send request to
            params (dict, optional): Dictionary of URL parameters to append to the URL. Defaults to None.
            data (Union[str, dict], optional): Data to send to request. Defaults to None.
            headers (dict, optional): Dictionary of HTTP headers to send with the request. Defaults to None.
            form (dict, optional): Form data to send with the request. Defaults to None.
            multipart (dict, optional): Multipart data to send with the request. Defaults to None.
            timeout (float, optional): Timeout in seconds. Defaults to 30.
            verify (bool, optional): Verify the server's TLS certificate. Defaults to True.
            max_redirects (int, optional): Maximum number of redirects to follow. Defaults to None.
        '''
        # Convert headers to dict if a CaseInsensitiveDict was provided
        if isinstance(headers, CaseInsensitiveDict):
            headers = dict(headers)

        # Define the asynchronous task
        async def task():
            # Access the original context object
            context_obj = self.context._obj  # Get the underlying BrowserContext
            # Await the fetch coroutine
            pywr_resp = await context_obj.request.fetch(
                url,
                params=params,
                method=method.lower(),
                headers=headers,
                data=data,
                form=form,
                multipart=multipart,
                timeout=int(timeout * 1e3),
                fail_on_status_code=False,
                ignore_https_errors=not verify,
                max_redirects=max_redirects,
            )
            # Await the body coroutine
            content = await pywr_resp.body()
            # Get cookies directly from the context
            browser_cookies = await context_obj.cookies()
            cookiejar = list_to_cookiejar(browser_cookies)
            # Create the response object
            resp = Response(
                raw=content,
                url=pywr_resp.url,
                status_code=pywr_resp.status,
                cookies=cookiejar,
                headers=CaseInsensitiveDict(pywr_resp.headers),
            )
            resp.session = self.session
            # Dispose of the response object
            await pywr_resp.dispose()
            return resp

        # Execute the asynchronous task synchronously
        return self.engine.execute(task)

    def get(self, url: str, **kwargs):
        return self.request('GET', url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self.request('PATCH', url, **kwargs)

    def put(self, url: str, **kwargs):
        return self.request('PUT', url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request('POST', url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request('DELETE', url, **kwargs)

    def head(self, url: str, **kwargs):
        return self.request('HEAD', url, **kwargs)

    def setHeaders(self, headers: Union[dict, CaseInsensitiveDict]):
        '''
        Set the browser headers

        Parameters:
            headers (Union[dict, CaseInsensitiveDict]): Headers to set
        '''
        self._headers = {
            **headers,
            # convert lists to comma separated
            **{k: ', '.join(v) for k, v in headers.items() if isinstance(v, list)},
        }
        self.context.set_extra_http_headers(self._headers)

    def loadText(self, text):
        # load content into page
        self.page.set_content(text)
        self.page.wait_for_load_state('domcontentloaded')

    def setCookies(self, cookiejar: RequestsCookieJar):
        # convert cookiejar to list of dicts
        cookie_renders = cookiejar_to_list(cookiejar)
        # set cookies in playwright instance
        self.context.add_cookies(cookie_renders)

    def close(self):
        if self._closed:
            # Browser was closed, nothing to do
            return
        cookiejar = self.getCookies()
        # Update session if provided
        if self.session:
            self.session.cookies = cookiejar
        # Update response
        if self.resp is not None:
            self.resp.cookies = cookiejar
            self.resp.raw = self.page.content()
            self.resp.url = self.page.url
            self.resp.status_code = self.status_code
        # Close browser
        self.shutdown()

    def __del__(self):
        self.close()


def render(
    url: Optional[str] = None,
    *,
    headless: bool = True,
    proxy: Optional[Union[str, BaseProxy]] = None,
    response: Optional[hrequests.response.Response] = None,
    session: Optional[hrequests.session.TLSSession] = None,
    browser: Literal['firefox', 'chrome'] = 'firefox',
    **kwargs,
):
    assert any(
        (url, session, response is not None)
    ), 'Must provide a url or an existing session, response'

    render_session = BrowserSession(
        session=session,
        resp=response,
        proxy=proxy,
        headless=headless,
        browser=browser,
        **kwargs,
    )
    # include headers from session if a TLSSession is provided
    if session and isinstance(session, hrequests.session.TLSSession):
        render_session.headers = session.headers
    # include merged cookies from session or from response
    if req_src := session or response:
        if req_src.cookies is not None:
            render_session.cookies = req_src.cookies
    if url:
        # goto url if url was provided
        render_session.goto(url)
    return render_session
