import asyncio
import functools
from abc import ABC, abstractmethod
from concurrent.futures import Future
from importlib.util import find_spec
from threading import Event, Lock, Thread
from typing import Callable, Dict, Optional, Set

from async_class import AsyncObject
from typing_extensions import Literal, ParamSpec, TypeVar

from hrequests import BROWSER_SUPPORT
from hrequests.exceptions import MissingLibraryException

try:
    from patchright.async_api import async_playwright as async_patchright
except ImportError:
    pass

try:
    from playwright.async_api import Browser as PWBrowser
    from playwright.async_api import async_playwright
except ImportError:
    pass


T = TypeVar("T")
P = ParamSpec("P")


class AbstractBrowserClient(AsyncObject, ABC):
    """
    Implementation of Playwright that is threadsafe, and supports both sync and async addons.
    """

    async def __ainit__(
        self,
        engine: 'BrowserEngine',
        proxy: Optional[Dict[str, str]] = None,
        verify: bool = True,
        *args,
        **kwargs,
    ):
        """
        Creates a new browser and context to be ran given an existing BrowserEngine.
        """
        self.engine = engine
        self.main_browser: Optional[PWBrowser] = None
        self.verify = verify
        self.proxy = proxy

        # Launching browser
        context_ptr = self.create_instance(*args, **kwargs)
        self.context = BrowserObjectWrapper(context_ptr, self.engine)

    def new_page(self):
        """
        Create a new page
        """
        page_ptr = self.context.new_page()
        return BrowserObjectWrapper(page_ptr, self.engine)

    def stop(self):
        """
        Stop the browser
        """
        if self.main_browser:
            self.engine.execute(self.main_browser.close)

    def create_instance(self, **kwargs):
        """
        Create a new browser instance
        """
        return self.engine.execute(self._start_context, **kwargs)

    @abstractmethod
    async def _start_context(self, **launch_args):
        """
        Create a new browser context
        """
        ...


class BrowserEngine:
    '''
    Wrapper around Playwright to manage it in a separate thread.
    Inspired by Medialab's threadsafe implementation of Playwright
    https://github.com/medialab/minet/blob/master/minet/browser/threadsafe_browser.py
    '''

    def __init__(self, browser_type: Literal['firefox', 'chrome'] = 'firefox') -> None:
        assert_browser(browser_type)
        self.browser_type = browser_type
        self.loop = asyncio.new_event_loop()
        self.start_event = Event()
        self.thread = Thread(
            target=self.__thread_worker, name=f"Hrequests-{browser_type}-{id(self)}"
        )

        self.running_futures: Set[Future] = set()
        self.running_futures_lock = Lock()

        # Launch the thread and the process in the background
        self.thread.start()

    async def __start_playwright(self):
        if self.browser_type == 'firefox':
            self.playwright = await async_playwright().start()
        elif self.browser_type == 'chrome':
            self.playwright = await async_patchright().start()
        else:
            raise ValueError(f"Invalid browser type: {self.browser_type}")

        return self.playwright

    async def __stop_playwright(self) -> None:
        # This kills playwright and all associated browsers and contexts
        await self.playwright.stop()

    def stop(self) -> None:
        with self.running_futures_lock:
            for future in self.running_futures:
                if not future.done():
                    future.cancel()

        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()

    def __del__(self):
        self.stop()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stop()

    def __thread_worker(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.__start_playwright())
        self.start_event.set()

        # We are now ready to accept tasks
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.run_until_complete(self.__stop_playwright())

    def __handle_future(self, future: Future):
        with self.running_futures_lock:
            self.running_futures.add(future)
        try:
            return future.result()
        finally:
            with self.running_futures_lock:
                self.running_futures.remove(future)

    def execute(self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        # wait if the engine has not started yet
        self.start_event.wait()
        future: Future = asyncio.run_coroutine_threadsafe(fn(*args, **kwargs), self.loop)
        return self.__handle_future(future)


class BrowserObjectWrapper:
    """
    Wraps around asynchronous Playwright objects to make them synchronous,
    and executes them in the engine's event loop thread.
    """

    def __init__(self, obj, engine):
        # Use __setattr__ to set internal attributes without triggering __getattribute__
        object.__setattr__(self, '_obj', obj)
        object.__setattr__(self, '_engine', engine)

    def __getattribute__(self, name):
        """
        Execute attributes in engine loop. Uses really hacky work arounds.
        """
        # Handle internal attributes directly
        if name in ('_obj', '_engine', '_wrap_result'):
            return object.__getattribute__(self, name)

        _obj = object.__getattribute__(self, '_obj')
        _engine = object.__getattribute__(self, '_engine')
        attr = getattr(_obj, name)

        if callable(attr):
            # Wraps asynchronous methods to make them synchronous
            @functools.wraps(attr)
            def method(*args, **kwargs):
                result = attr(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    # If result is a coroutine, schedule it in the event loop
                    async def task():
                        res = await result
                        return self._wrap_result(res)

                    return _engine.execute(task)
                else:
                    # Synchronous method; wrap the result if necessary
                    return self._wrap_result(result)

            return method

        elif asyncio.iscoroutine(attr):
            # Awaitable property, schedule it in the event loop
            async def task():
                result = await attr
                return self._wrap_result(result)

            return _engine.execute(task)

        elif hasattr(attr, '__dict__'):
            # Wrap objects with attributes (nested Playwright objects)
            return BrowserObjectWrapper(attr, _engine)

        else:
            # Return other attributes directly
            return attr

    def _wrap_result(self, result):
        # Wrap Playwright objects that have attributes and a 'close' method
        if hasattr(result, '__dict__') and hasattr(result, 'close'):
            return BrowserObjectWrapper(result, self._engine)
        return result


def assert_browser(browser: Literal['firefox', 'chrome']) -> None:
    if not BROWSER_SUPPORT:
        raise MissingLibraryException(
            'Browsing libraries are not installed. Please run `pip install hrequests[all]`'
        )
    if browser == 'firefox' and not find_spec('camoufox'):
        raise MissingLibraryException(
            'Camoufox is not installed. Please run `pip install hrequests[firefox]`'
        )
    if browser == 'chrome' and not find_spec('patchright'):
        raise MissingLibraryException(
            'Patchright is not installed. Please run `pip install hrequests[chrome]`'
        )
