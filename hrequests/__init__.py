'''
Hrequests initializer
'''

import os


def detect_module() -> bool:
    '''
    Hacky way to detect if hrequests is being ran as a module
    '''
    import inspect

    stack: list = inspect.stack(2)
    if len(stack) < 2:
        return False
    prev, launch = stack[-2:]
    try:
        if (launch.function, prev.function) == ('_run_module_as_main', '_get_module_details'):
            return True
    except AttributeError:
        pass
    return False


if detect_module():
    os.environ['HREQUESTS_MODULE'] = '1'


from .response import Response, ProcessResponse
from .session import Session, TLSSession, chrome, firefox
from .reqs import *
from .headers import Headers


# attempt to import headless browsing dependencies
try:
    from .playwright_mock import ChromeBrowser, FirefoxBrowser
    from .browser import BrowserSession, render
except ModuleNotFoundError:
    from rich import print as rprint

    if not os.getenv('HREQUESTS_MODULE'):
        rprint(
            '[bright_yellow]WARNING: Please run [white]pip install hrequests\[all][/] for headless browsing support.'
        )

from .parser import HTML
from .__version__ import __version__
from .__version__ import __author__
