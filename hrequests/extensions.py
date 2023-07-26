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


async def activate_exts(page, exts: List[Extension]):
    for ext in exts:
        await page.goto(ext.url)
        await page.evaluate(
            "document.querySelector('extensions-manager').shadowRoot"
            ".querySelector('#viewManager > extensions-detail-view.active').shadowRoot"
            ".querySelector('div#container.page-container > div.page-content > div#options-section extensions-toggle-row#allow-incognito').shadowRoot"
            ".querySelector('label#label input').click()"
        )
    await page.goto('about:blank')
