from typing import List, Tuple

from async_class import AsyncObject
from hrequests.playwright_mock import Faker, ProxyManager, context
from playwright.async_api import async_playwright


class PlaywrightMock(AsyncObject):
    async def __ainit__(
        self,
        headless: bool = False,
        scroll_into_view: bool = True,
        extensions=None,
    ):
        # setting values
        self.scroll_into_view = scroll_into_view
        self.extensions = extensions
        # starting Playwright
        self.playwright = await async_playwright().start()
        # launching chromium
        self.main_browser = await self.launch_browser(headless=headless)

    args: Tuple[str] = (
        '--disable-blink-features=AutomationControlled',
        '--disable-web-security',
        '--disable-site-isolation-trials',
        '--disable-features=CrossSiteDocumentBlockingIfIsolating,'
        'CrossSiteDocumentBlockingAlways,'
        'IsolateOrigins,'
        'site-per-process,'
        'SharedArrayBuffer',
    )  # type: ignore

    async def launch_browser(self, headless: bool = False):
        args: List[str] = list(PlaywrightMock.args)
        if headless:
            args.append('--headless=new')
        if self.extensions:
            paths = [ext.path for ext in self.extensions]
            args.extend(f'--load-extension={ext}' for ext in paths)
            args.append(f'--disable-extensions-except={",".join(paths)}')
        return await self.playwright.chromium.launch(headless=headless, args=args)

    async def stop(self):
        await self.main_browser.close()
        await self.playwright.stop()

    async def new_context(self, browser_name: str, user_agent: str, proxy=None, **launch_args):
        # calling proxyManager and faker
        _proxy = await ProxyManager(self, proxy)
        _faker = await Faker(self, _proxy, browser_name, user_agent)
        # create context with human emulation
        _browser = await context.new_context(
            self, _proxy, _faker, bypass_csp=True, user_agent=user_agent, **launch_args
        )
        _browser.proxy = _proxy
        _browser.faker = _faker

        return _browser
