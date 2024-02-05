import ctypes
import glob
import os
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
    # specify specific version of hrequests-cgo library
    BRIDGE_VERSION = '2.'

    def __init__(self):
        self.parent_path = os.path.join(root_dir, 'bin')
        self.file_cont, self.file_ext = self.get_name()
        self.file_pref = f'hrequests-cgo-{self.BRIDGE_VERSION}'
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
        files = sorted(glob.glob('hrequests-cgo-*', root_dir=self.parent_path), reverse=True)
        for file in files:
            if not file.endswith(self.file_ext):
                continue
            if file.startswith(self.file_pref):
                return file
            # delete residual files from previous versions
            os.remove(os.path.join(self.parent_path, file))
        self.download_library()
        return self.check_library()

    def check_assets(self, assets):
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

    def download_library(self):
        print('Downloading hrequests-cgo library from daijro/hrequests...')
        # pull release assets from github daijro/hrequests
        resp = get('https://api.github.com/repos/daijro/hrequests/releases')
        releases = loads(resp.content)
        for release in releases:
            asset = self.check_assets(release['assets'])
            if asset:
                url, name = asset
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


class GoString(ctypes.Structure):
    # wrapper around Go's string type
    _fields_ = [("p", ctypes.c_char_p), ("n", ctypes.c_longlong)]


# load the shared package
libman = LibraryManager()
library = ctypes.cdll.LoadLibrary(libman.full_path)
del libman

# extract the exposed DestroySession function
library.DestroySession.argtypes = [GoString]
library.DestroySession.restype = ctypes.c_void_p


def destroy_session(session_id: str):
    library.DestroySession(gostring(session_id))


# extract the exposed GetOpenPort function
library.GetOpenPort.restype = ctypes.c_int


def GetOpenPort():
    return library.GetOpenPort()


# spawn the server
PORT = GetOpenPort()
if not PORT:
    raise OSError('Could not find an open port.')

# extract the exposed StartServer and StopServer functions
library.StartServer.argtypes = [GoString]
library.StopServer.restype = ctypes.c_void_p


def gostring(s: str) -> GoString:
    port_buf = ctypes.create_string_buffer(s.encode('utf-8'))
    return GoString(ctypes.cast(port_buf, ctypes.c_char_p), len(s))


def start_server():
    library.StartServer(gostring(str(PORT)))


def stop_server():
    library.StopServer()


start_server()
