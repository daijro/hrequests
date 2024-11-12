from importlib.util import find_spec
from typing import Literal

import hrequests
from hrequests import BROWSER_SUPPORT
from hrequests.browser.engine import assert_browser

# Import the optional dependencies
try:
    from playwright._impl._errors import Error as PlaywrightError

    from .firefox import FirefoxBrowserClient
except ModuleNotFoundError:
    pass
try:
    from patchright._impl._errors import Error as PatchrightError

    from .chrome import ChromeBrowserClient
except ModuleNotFoundError:
    pass

# Get the error message for each
if BROWSER_SUPPORT:
    if find_spec('camoufox') and find_spec('patchright'):
        ERROR = (PlaywrightError, PatchrightError)
    elif find_spec('camoufox'):
        ERROR = (PlaywrightError,)
    elif find_spec('patchright'):
        ERROR = (PatchrightError,)
else:
    ERROR = ()


async def browser_client(
    browser_type: Literal['firefox', 'chrome'], **kwargs
) -> 'hrequests.browser.engine.AbstractBrowserClient':
    """
    A common handler that throws errors when a browser is passed that is not installed.
    """
    assert_browser(browser_type)

    if browser_type == 'firefox':
        return await FirefoxBrowserClient(**kwargs)

    if browser_type == 'chrome':
        return await ChromeBrowserClient(**kwargs)
