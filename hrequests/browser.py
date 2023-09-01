import asyncio
import os
from functools import partial
from random import choice
from threading import Thread
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional, Pattern, Union

from aioprocessing import Queue
from fake_headers import Headers
from playwright._impl._api_types import Error as PlaywrightError
from playwright._impl._api_types import TimeoutError as PlaywrightTimeoutError

import hrequests
from hrequests.client import CaseInsensitiveDict
from hrequests.cookies import cookiejar_to_list, list_to_cookiejar
from hrequests.exceptions import BrowserException, BrowserTimeoutException, JavascriptException
from hrequests.response import Response

from .cookies import RequestsCookieJar
from .extensions import BuildExtensions, Extension, activate_exts


class BrowserSession:
    """
    Args:
        headless (bool, optional): Whether to run the browser in headless mode. Defaults to True.
        session (hrequests.session.TLSSession, optional): Session to use for headers, cookies, etc.
        resp (hrequests.response.Response, optional): Response to update with cookies, headers, etc.
        proxy_ip (str, optional): Proxy to use for the browser. Example: 123.123.123
        mock_human (bool, optional): Whether to emulate human behavior. Defaults to False.
        browser (Literal['firefox', 'chrome', 'opera'], optional): Generate useragent headers for a specific browser
        os (Literal['win', 'mac', 'lin'], optional): Generate headers for a specific OS
        extensions (Union[str, Iterable[str]], optional): Path to a folder of unpacked extensions, or a list of paths to unpacked extensions

    Attributes:
        url (str): Get the page url
        headers (dict): Get the browser headers (User-Agent)
        content (dict): Get the current page content
        cookies (RequestsCookieJar): Get the browser cookies

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
        screenshot(path, full_page): Take a screenshot of the page
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
        headless: bool = True,
        session: Optional[hrequests.session.TLSSession] = None,
        resp: Optional[hrequests.response.Response] = None,
        proxy_ip: Optional[str] = None,
        mock_human: bool = False,
        browser: Optional[Literal['firefox', 'chrome', 'opera']] = None,
        os: Optional[Literal['win', 'mac', 'lin']] = None,
        extensions: Optional[Union[str, Iterable[str]]] = None,
    ) -> None:
        # uses asyncio queues to communicate with the asyncio loop from any thread
        # _in is for calls from other threads
        self._in: Queue = Queue()
        # _out is for responses from the asyncio loop
        self._out: Queue = Queue()
        # remember session and resp to clone cookies back to when closing
        self.session: Optional[hrequests.session.TLSSession] = session
        self.resp: Optional[hrequests.response.Response] = resp
        # generating headers
        if session:
            # if a session was provided, use the session user-agent
            self.browser: str = session.browser
            self.ua: str = session.headers.get('User-Agent')
        else:
            # if a browser or os was provided, generate a user-agent and IGNORE session/resp headers
            # only meant to be used when using BrowserSession as a standalone
            self.browser: str = browser or choice(('firefox', 'chrome', 'opera'))
            self.ua: str = Headers(browser=self.browser, os=os).generate()['User-Agent']
        # proxy variables
        self.proxy_ip: Optional[str] = proxy_ip
        # browser config
        self.mock_human: bool = mock_human
        self.headless: bool = headless
        self.extensions: Optional[List[Extension]] = (
            BuildExtensions(extensions).list if extensions else None
        )
        # bool to indicate browser was closed
        self._closed: bool = False
        # spawn asyncio loop
        thread: Thread = Thread(target=self.spawn_main, daemon=True)
        thread.start()

    def spawn_main(self) -> None:
        asyncio.new_event_loop().run_until_complete(self.main())

    async def main(self) -> None:
        # build the playwright instance
        self.client = await hrequests.PlaywrightMock(
            headless=self.headless, extensions=self.extensions
        )
        self.context = await self.client.new_context(
            browser_name=self.browser,
            user_agent=self.ua,
            proxy=self.proxy_ip,
            mock_human=self.mock_human,
        )
        # create a new page
        self.page = await self.context.new_page()
        # activate extensions
        if self.extensions:
            await activate_exts(self.page, self.extensions)
        '''
        run the main loop
        '''
        while True:
            try:
                # listen for calls to _in
                call: partial = self._in.get()
                # handle the call within the asyncio loop
                # this is used as a workaround to make playwright work across threads
                out = await call()
            except PlaywrightTimeoutError as e:
                # if a timeout error is raised, mark as closed and put the error in _out
                self._closed = True
                self._out.put(BrowserTimeoutException(e))
            except PlaywrightError as e:
                # if a playwright error is raised, mark as closed and put the error in _out
                self._closed = True
                self._out.put(BrowserException(e))
            except BrowserException as e:
                self._out.put(e)
            else:
                # put the call response in _out
                self._out.put(out)

    async def shutdown(self) -> None:
        self._closed = True
        await self.client.stop()

    def __enter__(self) -> 'BrowserSession':
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def _call_wrapper(self, func, *args, **kwargs) -> Any:
        # the call will then be ran within the asyncio loop,
        # which will launch the corresponding function with a leading underscore
        # then return the result
        self._in.put(partial(func, *args, **kwargs))
        out = self._out.get()
        if isinstance(out, Exception):
            raise out
        return out

    def __getattr__(self, name) -> Any:
        # sourcery skip: raise-from-previous-error
        if self._closed:
            raise BrowserException(f'Browser was closed. Attribute call failed: {name}')
        # forwards unknown attribute calls to _call_wrapper
        try:
            # check if the attribute (with a leading _) exists
            attr = self.__getattribute__(f'_{name}')
        except AttributeError:
            # if it doesn't, raise an error
            raise AttributeError(
                "'{obj_name}' object has no attribute '{attr_name}'".format(
                    obj_name=self.__class__.__name__, attr_name=name
                )
            )
        return partial(self._call_wrapper, attr)

    """
    Common public functions
    """

    async def _goto(self, url):
        '''Navigate to a URL'''
        return await self.page.goto(url)

    async def _forward(self):
        '''Navigate to the next page in history'''
        return await self.page.go_forward()

    async def _back(self):
        '''Navigate to the previous page in history'''
        return await self.page.go_back()

    async def _awaitNavigation(self, timeout: float = 30):
        '''
        Wait for the page navigation to finish

        Parameters:
            timeout (float, optional): Timeout in seconds. Defaults to 30.
        '''
        return await self.page.wait_for_load_state(timeout=int(timeout * 1e3))

    async def _awaitScript(self, script: str, arg: Optional[str] = None, *, timeout: float = 30):
        '''
        Wait for a script to return true

        Parameters:
            script (str): Script to evaluate
            arg (str, optional): Argument to pass to script
            timeout (float, optional): Timeout in seconds. Defaults to 30.
        '''
        return await self.page.wait_for_function(script, arg=arg, timeout=int(timeout * 1e3))

    async def _awaitSelector(self, selector, *, timeout: float = 30):
        '''
        Wait for a selector to exist

        Parameters:
            selector (str): Selector to wait for
            timeout (float, optional): Timeout in seconds. Defaults to 30.
        '''
        await self.page.wait_for_function(
            "selector => !!document.querySelector(selector)",
            arg=selector,
            timeout=int(timeout * 1e3),
        )

    async def _awaitEnabled(self, selector, *, timeout: float = 30):
        '''
        Wait for a selector to be enabled

        Parameters:
            selector (str): Selector to wait for
            timeout (float, optional): Timeout in seconds. Defaults to 30.
        '''
        await self.page.wait_for_function(
            "selector => !document.querySelector(selector).disabled",
            arg=selector,
            timeout=int(timeout * 1e3),
        )

    async def _isVisible(self, selector: str) -> bool:
        '''
        Check if a selector is visible

        Parameters:
            selector (str): Selector to check
        '''
        return await self.page.is_visible(selector)

    async def _isEnabled(self, selector: str) -> bool:
        '''
        Check if a selector is enabled

        Parameters:
            selector (str): Selector to check
        '''
        if not await self.page.is_visible(selector):
            return False
        return await self.page.evaluate(
            "selector => !document.querySelector(selector).disabled", arg=selector
        )

    async def _awaitUrl(
        self, url: Union[str, Pattern[str], Callable[[str], bool]], *, timeout: float = 30
    ):
        '''
        Wait for the url to match a string, regex, or a python function to return True

        Parameters:
            url (Union[str, Pattern[str], Callable[[str], bool]]) - URL to match for
            timeout (float, optional): Timeout in seconds. Defaults to 30.
        '''
        return await self.page.wait_for_url(url, timeout=int(timeout * 1e3))

    async def _dragTo(
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
        return await self.page.drag_and_drop(
            source, target, no_wait_after=not wait_after, timeout=int(timeout * 1e3), check=check
        )

    async def _type(self, selector: str, text: str, delay: int = 50, *, timeout: float = 30):
        '''
        Type text into a selector

        Parameters:
            selector (str): CSS selector to type in
            text (str): Text to type
            delay (int, optional): Delay between keypresses in ms. On mock_human, this is randomized by 50%. Defaults to 50.
            timeout (float, optional): Timeout in seconds. Defaults to 30.
        '''
        return await self.page.type(selector, text, delay=delay, timeout=int(timeout * 1e3))

    async def _click(
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
        return await self.page.click(
            selector,
            button=button,
            click_count=count,
            timeout=int(timeout * 1e3),
            no_wait_after=not wait_after,
        )

    async def _hover(
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
        return await self.page.hover(selector, modifiers=modifiers, timeout=int(timeout * 1e3))

    async def _evaluate(self, script: str, arg: Optional[str] = None):
        '''
        Evaluate and return javascript

        Parameters:
            script (str): Javascript to evaluate in the page
            arg (str, optional): Argument to pass into the javascript function
        '''
        try:
            return await self.page.evaluate(script, arg=arg)
        except PlaywrightError as e:
            raise JavascriptException('Javascript eval exception') from e

    async def _screenshot(self, path: str, full_page: bool = False):
        '''
        Take a screenshot of the page

        Parameters:
            path (str): Path to save screenshot to
            full_page (bool): Whether to take a screenshot of the full scrollable page
        '''
        return await self.page.screenshot(path=path, full_page=full_page)

    '''
    .url, .content, .cookies, .html properties
    makes this compatible with TLSSession
    '''

    async def _getContent(self):
        '''Get the page content'''
        return await self.page.content()

    async def _getCookies(self) -> RequestsCookieJar:
        '''Get the page cookies'''
        browser_cookies: list = await self.context.cookies()
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
        return CaseInsensitiveDict({'User-Agent': self.ua})

    @headers.setter
    def headers(self, headers: dict):
        '''Set headers'''
        self.setHeaders(headers)

    @property
    def content(self) -> str:
        '''Get the page url'''
        return self.getContent()

    @property
    def proxies(self):
        return {'all': self.proxy_ip} if self.proxy_ip else {}

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
        '''Get the page html as anHTML object'''
        return hrequests.parser.HTML(
            session=self, url=self.url, html=self.content, default_encoding='utf-8'
        )

    '''
    Network request functions
    '''

    async def _request(
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
        # convert headers to dict if a CaseInsensitiveDict was provided
        if isinstance(headers, CaseInsensitiveDict):
            headers = dict(headers)
        pywr_resp = await self.context.request.fetch(
            url,
            params=params,
            method=method.lower(),
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=int(timeout * 1e3),
            ignore_https_errors=not verify,
            max_redirects=max_redirects,
        )
        content = await pywr_resp.body()
        resp = Response(
            _content=content,
            url=pywr_resp.url,
            status_code=pywr_resp.status,
            cookies=await self._getCookies(),
            headers=CaseInsensitiveDict(pywr_resp.headers),
        )
        resp.session = self.session
        await pywr_resp.dispose()
        return resp

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

    async def _setHeaders(self, headers: Union[dict, CaseInsensitiveDict]):
        '''
        Set the browser headers

        Parameters:
            headers (Union[dict, CaseInsensitiveDict]): Headers to set
        '''
        await self.context.set_extra_http_headers(
            {
                **headers,
                # convert lists to comma separated
                **{k: ', '.join(v) for k, v in headers.items() if isinstance(v, list)},
            }
        )

    async def _loadText(self, text):
        # load content into page
        await self.page.set_content(text)
        await self.page.wait_for_load_state()

    async def _setCookies(self, cookiejar: RequestsCookieJar):
        # convert cookiejar to list of dicts
        cookie_renders = cookiejar_to_list(cookiejar)
        # set cookies in playwright instance
        await self.context.add_cookies(cookie_renders)

    async def _close(self):
        if self._closed:
            # browser was closed, nothing to do
            return
        cookiejar = await self._getCookies()
        # update session if provided
        if self.session:
            self.session.cookies = cookiejar
        # update response
        if self.resp:
            self.resp.cookies = cookiejar
            self.resp._content = await self.page.content()
            self.resp._text = None
            self.resp.url = self.page.url
        # close browser
        await self.shutdown()

    def __del__(self):
        self.close()


def render(
    url: str = None,
    headless: bool = True,
    proxy: dict = None,
    response: hrequests.response.Response = None,
    session: hrequests.session.TLSSession = None,
    mock_human: bool = False,
    extensions: Optional[Union[str, Iterable[str]]] = None,
):
    assert any((url, session, response)), 'Must provide a url or an existing session, response'
    if proxy:
        proxy = list(proxy.values())[0]
    render_session = BrowserSession(
        session=session,
        resp=response,
        proxy_ip=proxy,
        headless=headless,
        mock_human=mock_human,
        extensions=extensions,
    )
    # include headers from session if a TLSSession is provided
    if session and isinstance(session, hrequests.session.TLSSession):
        render_session.setHeaders(session.headers)
    # include merged cookies from session or from response
    if req_src := session or response:
        render_session.setCookies(req_src.cookies)
    if url:
        # goto url if url was provided
        render_session.goto(url)
    else:
        # load response content if a response was provided
        render_session.loadText(response.text)
    return render_session
