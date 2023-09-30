import ctypes
import os
import socket
from platform import machine
from sys import platform
from typing import Tuple

import rich.progress
from httpx import get, stream
from orjson import loads

root_dir = os.path.abspath(os.path.dirname(__file__))

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
    def __init__(self):
        self.parent_path = os.path.join(root_dir, 'bin')
        self.file_cont, self.file_ext = self.get_name()
        filename = self.check_library()
        self.full_path = os.path.join(self.parent_path, filename)

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

    def check_library(self):
        for file in os.listdir(self.parent_path):
            if file.endswith(self.file_ext):
                return file
        self.download_library()
        return self.check_library()

    def download_library(self):
        print('Downloading hrequests-cgo library from daijro/hrequests...')
        # pull release assets from github daijro/hrequests
        resp = get('https://api.github.com/repos/daijro/hrequests/releases/latest')
        assets = loads(resp.content)['assets']
        for asset in assets:
            if self.file_cont in asset['name'] and asset['name'].endswith(self.file_ext):
                url: str = asset['browser_download_url']
                name: str = asset['name']
                break
        else:
            raise IOError('Could not find a matching binary for your system.')
        with open(os.path.join(self.parent_path, name), 'wb') as fstream:
            self.download_file(fstream, url)

    @staticmethod
    def download_file(fstream, url):
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


def GetOpenPort() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


class GoString(ctypes.Structure):
    # wrapper around Go's string type
    _fields_ = [("p", ctypes.c_char_p), ("n", ctypes.c_longlong)]


# load the shared package
libman = LibraryManager()

library = ctypes.cdll.LoadLibrary(libman.full_path)
del libman

# extract the exposed destroySession function
library.DestroySession.argtypes = [GoString]
library.DestroySession.restype = ctypes.c_void_p


def destroySession(session_id: str):
    encoded_session_id = session_id.encode('utf-8')
    library.DestroySession(GoString(encoded_session_id, len(encoded_session_id)))


# spawn the server
PORT = GetOpenPort()
library.StartServer.argtypes = [GoString]


def start_server():
    encoded_port = str(PORT).encode('utf-8')
    library.StartServer(GoString(encoded_port, len(encoded_port)))


start_server()
