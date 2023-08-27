from .response import Response, ProcessResponse
from .session import Session, TLSSession, chrome, firefox, opera
from .reqs import *

# attempt to import headless browsing dependencies
try:
    from .playwright_mock import PlaywrightMock
    from .browser import BrowserSession, render
except ModuleNotFoundError:
    import os
    from sys import stderr

    # give windows users a warning
    os.name == 'nt' and stderr.write(
        'WARNING: Please run `pip install hrequests[all]` for headless browsing support.\n'
    )

from .parser import HTML
from .__version__ import __version__
from .__version__ import __author__
