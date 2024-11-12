'''
Hrequests initializer
'''

import os
from importlib.util import find_spec


def _detect_module() -> bool:
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


if _detect_module():
    os.environ['HREQUESTS_MODULE'] = '1'


from .reqs import *
from .response import ProcessResponse, Response
from .session import Session, TLSSession, chrome, firefox

# attempt to import headless browsing dependencies
BROWSER_SUPPORT = str(int(bool(find_spec('camoufox') or find_spec('patchright'))))
if BROWSER_SUPPORT == '1':
    from .browser import BrowserEngine, BrowserSession, render
else:
    from rich import print as rprint

    if not os.getenv('HREQUESTS_MODULE'):
        rprint(
            r'[bright_yellow]WARNING: Please run [white]pip install hrequests\[all][/] for automated browsing support.'
        )

from .__version__ import __author__, __version__
from .parser import HTML
