import ctypes
import os
from pathlib import Path
from platform import machine
from sys import platform
from typing import Optional, Tuple

import rich.progress
from geventhttpclient import HTTPClient
from httpx import get, stream
from orjson import loads

from hrequests.__version__ import BRIDGE_VERSION

root_dir: Path = Path(os.path.abspath(os.path.dirname(__file__)))

# map machine architecture to hrequests-cgo binary name
arch_map = {
    'amd64': 'amd64',
    'x86_64': 'amd64',
    'x86': '386',
    'i686': '386',
    'i386': '386',
    'arm64': 'arm64',
    'aarch64': 'arm64',
    'armv5l': 'arm-5',
    'armv6l': 'arm-6',
    'armv7l': 'arm-7',
    'ppc64le': 'ppc64le',
    'riscv64': 'riscv64',
    's390x': 's390x',
}


class LibraryManager:
    def __init__(self) -> None:
        self.parent_path: Path = root_dir / 'bin'
        self.file_cont, self.file_ext = self.get_name()
        self.file_pref = f'hrequests-cgo-{BRIDGE_VERSION}'
        filename = self.check_library()
        self.full_path: str = str(self.parent_path / filename)

    @staticmethod
    def get_name() -> Tuple[str, str]:
        try:
            arch = arch_map[machine().lower()]
        except KeyError as e:
            raise OSError('Your machine architecture is not supported.') from e
        if platform == 'darwin':
            return f'darwin-{arch}', '.dylib'
        elif platform in ('win32', 'cygwin'):
            return f'windows-4.0-{arch}', '.dll'
        return f'linux-{arch}', '.so'

    def get_files(self) -> list:
        files: list = [file.name for file in self.parent_path.glob('hrequests-cgo-*')]
        return sorted(files, reverse=True)

    def check_library(self) -> str:
        files: list = self.get_files()
        for file in files:
            if not file.endswith(self.file_ext):
                continue
            if file.startswith(self.file_pref):
                return file
            # delete residual files from previous versions
            os.remove(self.parent_path / file)
        self.download_library()
        return self.check_library()

    def check_assets(self, assets) -> Optional[Tuple[str, str]]:
        for asset in assets:
            if (
                # filter via version
                asset['name'].startswith(self.file_pref)
                # filter via os
                and self.file_cont in asset['name']
                # filter via file extension
                and asset['name'].endswith(self.file_ext)
            ):
                return asset['browser_download_url'], asset['name']

    def get_releases(self) -> dict:
        # pull release assets from github daijro/hrequests
        resp = get('https://api.github.com/repos/daijro/hrequests/releases')
        if resp.status_code != 200:
            raise ConnectionError(f'Could not connect to GitHub: {resp.text}')
        return loads(resp.content)

    def download_library(self):
        print('Downloading hrequests-cgo library from daijro/hrequests...')
        releases = self.get_releases()
        for release in releases:
            asset = self.check_assets(release['assets'])
            if asset:
                url, name = asset
                break
        else:
            raise IOError('Could not find a matching binary for your system.')
        # download file
        file = self.parent_path / name
        self.download_file(file, url)

    def download_file(self, file, url):
        # handle download_exec
        try:
            with open(file, 'wb') as fstream:
                self.download_exec(fstream, url)
        except KeyboardInterrupt as e:
            print('Cancelled.')
            os.remove(file)
            raise e

    @staticmethod
    def download_exec(fstream, url):
        # file downloader with progress bar
        total: int
        with stream('GET', url, follow_redirects=True) as resp:
            total = int(resp.headers['Content-Length'])
            with rich.progress.Progress(
                "[progress.percentage]{task.percentage:>3.0f}%",
                rich.progress.BarColumn(bar_width=40),
                rich.progress.DownloadColumn(),
                rich.progress.TransferSpeedColumn(),
            ) as progress:
                download_task = progress.add_task("Download", total=total)
                for chunk in resp.iter_bytes():
                    fstream.write(chunk)
                    progress.update(download_task, completed=resp.num_bytes_downloaded)

    @staticmethod
    def load_library() -> ctypes.CDLL:
        libman: LibraryManager = LibraryManager()
        return ctypes.cdll.LoadLibrary(libman.full_path)


class GoString(ctypes.Structure):
    # wrapper around Go's string type
    _fields_ = [("p", ctypes.c_char_p), ("n", ctypes.c_longlong)]


def gostring(s: str) -> GoString:
    # create a string buffer and keep a reference to it
    port_buf = ctypes.create_string_buffer(s.encode('utf-8'))
    # pass the buffer to GoString
    go_str = GoString(ctypes.cast(port_buf, ctypes.c_char_p), len(s))
    # attach the buffer to the GoString instance to keep it alive
    go_str._keep_alive = port_buf
    return go_str


class Library:
    def __init__(self) -> None:
        # load the shared package
        self.library: ctypes.CDLL = LibraryManager.load_library()

        # extract the exposed DestroySession function
        self.library.DestroySession.argtypes = [GoString]

        # extract the exposed GetOpenPort function
        self.library.GetOpenPort.argtypes = []
        self.library.GetOpenPort.restype = ctypes.c_int

    def launch(self) -> None:
        # spawn the server
        self.PORT = self.get_open_port()
        if not self.PORT:
            raise OSError('Could not find an open port.')

        # extract the exposed StartServer and StopServer functions
        self.library.StartServer.argtypes = [GoString]
        self.library.StopServer.argtypes = []

        self.start_server()

    def destroy_session(self, session_id: str):
        # destroy a session by its passed session_id
        ref: GoString = gostring(session_id)
        self.library.DestroySession(ref)

    def get_open_port(self) -> int:
        # generate a new open port
        return self.library.GetOpenPort()

    def start_server(self):
        # launch the server
        ref: GoString = gostring(str(self.PORT))
        self.library.StartServer(ref)

    def stop_server(self):
        # destroy the server
        self.library.StopServer()


library: Optional[Library]

if os.getenv('HREQUESTS_MODULE'):
    library = None
else:
    library = Library()
    library.launch()
