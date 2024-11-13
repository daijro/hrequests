import math
from importlib.util import find_spec
from typing import Tuple, Union

from .engine import AbstractBrowserClient

try:
    from camoufox.ip import Proxy as CFProxy
    from camoufox.ip import public_ip
    from camoufox.locale import get_geolocation
except ImportError:
    pass


class ChromeBrowserClient(AbstractBrowserClient):
    async def _start_context(self, **launch_args):
        """
        Create a new browser context
        """
        # Remove unsupported parameters
        assert not launch_args.pop(
            'humanize'
        ), "`mock_human` is not supported for Chrome browsing. Please use Firefox instead."
        # Remove parameters that hrequests will pass to Camoufox
        launch_args.pop('os', None)
        launch_args.pop('version', None)
        launch_args.pop('enable_cache', None)
        try:
            cmd = self.engine.playwright.chromium.launch(**launch_args, proxy=self.proxy)
        except TypeError as exc:
            raise TypeError(
                "Unsupported parameters passed to Chrome browser. "
                "If you are using Camoufox parameters, please use a Firefox BrowserSession "
                "instead."
            ) from exc
        browser = await cmd

        # Add pointer to the objects list to delete on shutdown
        self.main_browser = browser

        # Handle Patchright geolocation
        if not self.proxy or not find_spec('camoufox'):
            # Do not use extra geolocation if Camoufox is not installed
            return await browser.new_context(ignore_https_errors=not self.verify, proxy=self.proxy)

        # Get the IP address
        ip = public_ip(CFProxy(**self.proxy).as_string())
        geolocation = get_geolocation(ip).as_config()

        # Handle geolocation accuracy if not provided
        if not geolocation.get('geolocation:accuracy'):
            percision = _float_percision(
                (geolocation['geolocation:latitude'], geolocation['geolocation:longitude'])
            )
            geolocation['geolocation:accuracy'] = (
                111320 * math.cos(geolocation['geolocation:latitude'] * math.pi / 180)
            ) / math.pow(10, percision)

        # Return the context
        return await browser.new_context(
            ignore_https_errors=not self.verify,
            timezone_id=geolocation['timezone'],
            geolocation={
                'latitude': geolocation['geolocation:latitude'],
                'longitude': geolocation['geolocation:longitude'],
                'accuracy': geolocation['geolocation:accuracy'],
            },
        )


def _float_percision(value: Union[float, Tuple[float, ...]]) -> int:
    if isinstance(value, tuple):
        return min(map(_float_percision, value))
    return len(str(value).split('.', 1)[1].strip('0')) if '.' in str(value) else 0
