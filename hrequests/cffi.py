import ctypes
import os
from platform import machine
from sys import platform

from httpx import get, stream
import rich.progress
from orjson import loads

root_dir = os.path.abspath(os.path.dirname(__file__))

# map machine architecture to tls-client binary name
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
        self.file_name = self.get_path()
        filename = self.check_library()
        self.full_path = os.path.join(self.parent_path, filename)

    @staticmethod
    def get_path():
        try:
            arch = arch_map[machine().lower()]
        except KeyError as e:
            raise OSError('Your machine architecture is not supported.') from e
        if platform == 'darwin':
            return f'darwin-{arch}.dylib'
        elif platform in ('win32', 'cygwin'):
            return f'windows-{arch}.dll'
        return f'linux-{arch}.so'

    def check_library(self):
        for file in os.listdir(self.parent_path):
            if file.endswith(self.file_name):
                return file
        self.download_library()
        return self.check_library()

    def download_library(self):
        print('Downloading tls-client library from bogdanfinn/tls-client...')
        # pull release assets from github bogdanfinn/tls-client
        resp = get('https://api.github.com/repos/bogdanfinn/tls-client/releases/latest')
        assets = loads(resp.text)['assets']
        for asset in assets:
            if asset['name'].endswith(self.file_name):
                url = asset['browser_download_url']
                name = asset['name']
                break
        else:
            raise IOError('Could not find a matching tls-client binary for your system.')
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


libman = LibraryManager()

library = ctypes.cdll.LoadLibrary(libman.full_path)
del libman

# extract the exposed request function from the shared package
request = library.request
request.argtypes = [ctypes.c_char_p]
request.restype = ctypes.c_char_p


freeMemory = library.freeMemory
freeMemory.argtypes = [ctypes.c_char_p]
freeMemory.restype = ctypes.c_char_p


destroyAll = library.destroyAll
destroyAll.restype = ctypes.c_char_p
