from functools import partial
from typing import Dict, List, Tuple

from async_class import AsyncObject
from playwright.async_api import async_playwright

from hrequests.extensions import LoadFirefoxAddon
from hrequests.playwright_mock import Faker, ProxyManager, context
from hrequests.cffi import GetOpenPort


class PlaywrightMockBase(AsyncObject):
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

    args: Tuple[str]

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


class ChromeBrowser(PlaywrightMockBase):
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
        args: List[str] = list(self.args)
        if headless:
            args.append('--headless=new')
        if self.extensions:
            paths = [ext.path for ext in self.extensions]
            args.extend(f'--load-extension={ext}' for ext in paths)
            args.append(f'--disable-extensions-except={",".join(paths)}')
        return await self.playwright.chromium.launch(
            headless=headless, args=args, proxy={'server': 'per-context'}
        )


class FirefoxBrowser(PlaywrightMockBase):
    firefox_user_prefs: Dict[str, bool] = {
        'media.peerconnection.enabled': False,
        'media.navigator.enabled': False,
        'privacy.resistFingerprinting': False,
        'devtools.debugger.remote-enabled': True,
        'devtools.debugger.prompt-connection': False,
        'extensions.manifestV3.enabled': True,
    }

    async def launch_browser(self, headless: bool = False):
        run_cmd = partial(
            self.playwright.firefox.launch,
            headless=headless,
            firefox_user_prefs=self.firefox_user_prefs,
        )
        if not self.extensions:
            return await run_cmd()
        # block mv3
        for ext in self.extensions:
            assert not ext.is_mv3, f'MKV extensions are not supported: {ext.path}'
        rdp_port: int = GetOpenPort()
        pr = await run_cmd(
            args=('-start-debugger-server', str(rdp_port)),
        )
        for ext in self.extensions:
            ff_addon = LoadFirefoxAddon(rdp_port, ext.path)
            await ff_addon.load()
        return pr
