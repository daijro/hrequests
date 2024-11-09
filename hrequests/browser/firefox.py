from camoufox.async_api import AsyncNewBrowser

from .engine import AbstractBrowserClient


class FirefoxBrowserClient(AbstractBrowserClient):
    async def _start_context(self, **launch_args):
        """
        Create a new browser context
        """
        # Create a Camoufox browser
        browser = await AsyncNewBrowser(
            self.engine.playwright,
            geoip=launch_args.get('geoip', bool(self.proxy)),
            proxy=self.proxy,
            ff_version=launch_args.pop('version', None),
            i_know_what_im_doing=True,
            **launch_args,
        )

        # Add pointer to the objects list to delete on shutdown
        self.main_browser = browser

        # Return the Camoufox context
        return await browser.new_context(ignore_https_errors=not self.verify)
