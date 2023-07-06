import ctypes
import os
from platform import machine
from sys import platform
import re
import wget
from httpx import get
from orjson import loads

root_dir = os.path.abspath(os.path.dirname(__file__))


class LibraryManager:
    def __init__(self):
        self.parent_path = os.path.join(root_dir, 'bin')
        self.file_regex = re.compile(self.get_path())
        filename = self.check_library()
        self.full_path = os.path.join(self.parent_path, filename)

    @staticmethod
    def get_path():
        if platform == 'darwin':
            if machine() == "arm64":
                return r'.*darwin\-arm64\-.*\.dylib'
            else:
                return r'.*darwin\-amd64\-.*\.dylib'
        elif platform in ('win32', 'cygwin'):
            if ctypes.sizeof(ctypes.c_voidp) == 8:
                return r'.*windows\-64\-.*\.dll'
            else:
                return r'.*windows\-32\-.*\.dll'
        if machine() == "aarch64":
            return r'.*arm64\-.*\.so'
        if platform == 'linux':
            # check if alpine
            os_name_dat = os.popen('cat /etc/os-release').read()
            if not os_name_dat:
                return r'.*ubuntu\-amd64\-.*\.so'
            os_name = re.search(r'NAME="(\w+)"', os_name_dat)[1]
            if os_name.lower() == 'alpine':
                return r'.*alpine\-amd64\-.*\.so'
        return r'.*ubuntu\-amd64\-.*\.so'

    def check_library(self):
        for file in os.listdir(self.parent_path):
            if self.file_regex.match(file):
                return file
        self.download_library()
        return self.check_library()

    def download_library(self):
        print('Downloading tls-client library from bogdanfinn/tls-client...')
        # pull release assets from github bogdanfinn/tls-client
        resp = get('https://api.github.com/repos/bogdanfinn/tls-client/releases/latest')
        assets = loads(resp.text)['assets']
        for asset in assets:
            if self.file_regex.match(asset['name']):
                url = asset['browser_download_url']
                break
        else:
            raise IOError('Could not find a matching tls-client binary for your system.')
        wget.download(url, out=self.parent_path)
        print('')


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
