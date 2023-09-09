import asyncio
import hashlib
import logging
import os
from base64 import b64decode
from dataclasses import dataclass
from os.path import exists, isdir, join
from typing import Iterable, List, Union

import orjson
from Crypto.PublicKey import RSA


@dataclass
class Extension:
    '''
    Dataclass for managing Chrome extensions

    Args:
        path (str): path to the extension folder
    '''

    path: str

    def __post_init__(self):
        # open manifest.json
        manifest_path = join(self.path, 'manifest.json')
        assert exists(manifest_path), f'Extension "{self.path}" does not have a manifest.json file'
        # read manifest.json
        with open(manifest_path, 'rb') as f:
            manifest = orjson.loads(f.read())
        # check if manifest is mv3
        self.is_mv3: bool = manifest['manifest_version'] == 3
        # if the manifest has a 'key' field, use it to generate the extension id
        if 'key' in manifest:
            self.id: str = self.build_id(manifest['key'])
        # else, generate a random pub key to use instead
        else:
            manifest['key'] = self.generate_pub_key()
            self.id: str = self.build_id(manifest['key'])
            # write the new manifest.json
            with open(manifest_path, 'wb') as f:
                f.write(orjson.dumps(manifest, option=orjson.OPT_INDENT_2))
            logging.info(f'Generated new extension keypair ({self.id}) for "{self.path}"')

        self.url: str = f'chrome://extensions/?id={self.id}'

    @staticmethod
    def generate_pub_key() -> str:
        '''generate an RSA key and export it as a PKCS8 public key'''
        key = RSA.generate(2048)
        export = key.publickey().export_key(pkcs=8).decode('utf-8')
        return ''.join(export.split('\n')[1:-1])

    @staticmethod
    def build_id(pub_key_pem) -> str:
        '''build an extension id from a public key'''
        pub_key_der = b64decode(pub_key_pem)
        sha = hashlib.sha256(pub_key_der).hexdigest()
        prefix = sha[:32]
        return ''.join(chr(97 + int(old_char, 16)) for old_char in prefix)


class BuildExtensions:
    def __init__(self, extensions: Union[str, Iterable[str]]):
        self.list: List[Extension]

        # if `extension` is a string, assume it is a path to a folder of unpacked extensions
        if isinstance(extensions, str):
            assert isdir(extensions), 'Extension path must be a folder'
            # create a list of all the folders in the extension path
            self.list = []
            for item in os.listdir(extensions):
                path = join(extensions, item)
                if isdir(path):
                    self.list.append(Extension(path))
        # if `extension` is a list, assume it is a list of paths to unpacked extensions
        elif isinstance(extensions, list):
            assert all(isdir(path) for path in extensions), 'Extensions must be folders'
            self.list = [Extension(path) for path in extensions]


async def load_chrome_exts(page, exts: List[Extension]):
    for ext in exts:
        await page.goto(ext.url)
        await page.evaluate(
            "document.querySelector('extensions-manager').shadowRoot"
            ".querySelector('#viewManager > extensions-detail-view.active').shadowRoot"
            ".querySelector('div#container.page-container > div.page-content > div#options-section extensions-toggle-row#allow-incognito').shadowRoot"
            ".querySelector('label#label input').click()"
        )
    await page.goto('about:blank')


class LoadFirefoxAddon:
    '''
    Firefox addon loader
    Based on this Node.js implementation:
    https://github.com/microsoft/playwright/issues/7297#issuecomment-1211763085
    '''

    def __init__(self, port, addon_path):
        self.port: int = port
        self.addon_path: str = addon_path
        self.success: bool = False
        self.buffers: list = []
        self.remaining_bytes: int = 0

    async def load(self):
        reader, writer = await asyncio.open_connection('localhost', self.port)
        writer.write(self._format_message({"to": "root", "type": "getRoot"}))
        await writer.drain()

        while True:
            data = await reader.read(100)  # Adjust buffer size as needed
            if not data:
                break
            await self._process_data(writer, data)

        writer.close()
        await writer.wait_closed()
        return self.success

    async def _process_data(self, writer, data):
        while data:
            if self.remaining_bytes == 0:
                index = data.find(b':')
                if index == -1:
                    self.buffers.append(data)
                    return

                total_data = b''.join(self.buffers) + data
                size, _, remainder = total_data.partition(b':')

                try:
                    self.remaining_bytes = int(size)
                except ValueError as e:
                    raise ValueError("Invalid state") from e

                data = remainder

            if len(data) < self.remaining_bytes:
                self.remaining_bytes -= len(data)
                self.buffers.append(data)
                return
            else:
                self.buffers.append(data[: self.remaining_bytes])
                message = orjson.loads(b''.join(self.buffers))
                self.buffers.clear()

                await self._on_message(writer, message)

                data = data[self.remaining_bytes :]
                self.remaining_bytes = 0

    async def _on_message(self, writer, message):
        if "addonsActor" in message:
            writer.write(
                self._format_message(
                    {
                        "to": message["addonsActor"],
                        "type": "installTemporaryAddon",
                        "addonPath": self.addon_path,
                    }
                )
            )
            await writer.drain()

        if "addon" in message:
            self.success = True
            writer.write_eof()

        if "error" in message:
            writer.write_eof()

    def _format_message(self, data):
        raw = orjson.dumps(data)
        return f"{len(raw)}:".encode() + raw
