import os
import re
import subprocess
import sys
from dataclasses import dataclass
from functools import total_ordering
from importlib.util import find_spec
from pathlib import Path
from typing import Optional

import rich_click as click
from browserforge.download import Download
from rich import print as rprint
from rich.panel import Panel
from rich.status import Status

from hrequests.__version__ import BRIDGE_VERSION, __version__
from hrequests.cffi import LibraryManager, root_dir

try:
    from camoufox.__main__ import CamoufoxUpdate
    from camoufox.locale import download_mmdb, remove_mmdb
except ImportError:
    pass

'''
Hrequests library component manager
'''


@total_ordering
@dataclass
class Version:
    version: str

    def __post_init__(self) -> None:
        self.sort_version = tuple(int(x) for x in self.version.split('.'))

    def __eq__(self, other) -> bool:
        return self.sort_version == other.sort_version

    def __lt__(self, other) -> bool:
        return self.sort_version < other.sort_version

    def __str__(self) -> str:
        return self.version

    @staticmethod
    def get_version(name) -> 'Version':
        ver: Optional[re.Match] = LibraryUpdate.FILE_NAME.search(name)
        if not ver:
            raise ValueError(f'Could not find version in {name}')
        return Version(ver[1])


@dataclass
class Asset:
    url: str
    name: str

    def __post_init__(self) -> None:
        self.version: Version = Version.get_version(self.name)


class LibraryUpdate(LibraryManager):
    '''
    Checks if an update is avaliable for hrequests-cgo library
    '''

    FILE_NAME: re.Pattern = re.compile(r'^hrequests-cgo-([\d\.]+)')

    def __init__(self) -> None:
        self.parent_path: Path = root_dir / 'bin'
        self.file_cont, self.file_ext = self.get_name()
        self.file_pref = f'hrequests-cgo-{BRIDGE_VERSION}'

    @property
    def path(self) -> Optional[str]:
        if paths := self.get_files():
            return paths[0]

    @property
    def full_path(self) -> Optional[str]:
        if path := self.path:
            return os.path.join(self.parent_path, path)

    def latest_asset(self) -> Asset:
        '''
        Find the latest Asset for the hrequests-cgo library
        '''
        releases = self.get_releases()
        for release in releases:
            if asset := self.check_assets(release['assets']):
                url, name = asset
                return Asset(url, name)
        raise ValueError('No assets found for hrequests-cgo')

    def install(self) -> None:
        filename = super().check_library()
        ver: Version = Version.get_version(filename)

        rprint(
            f'[bright_green]:sparkles: Successfully installed hrequests-cgo v{ver}! :tada:[/]'
            '\nSee the documentation to get started: https://daijro.gitbook.io/hrequests'
        )

    def update(self) -> None:
        '''
        Updates the library if needed
        '''
        path = self.path
        if not path:
            # install the library if it doesn't exist
            return self.install()

        # get the version
        current_ver: Version = Version.get_version(path)

        # check if the version is the same as the latest avaliable version
        asset: Asset = self.latest_asset()
        if current_ver >= asset.version:
            rprint('[bright_green]:sparkles: hrequests-cgo library up to date! :tada:')
            rprint(f'Current version: [green]v{current_ver}')
            return

        # download updated file
        rprint(f'Updating hrequests-cgo library from [red]v{current_ver}[/] => v{asset.version}')
        # download new, remove old
        self.download_file(self.full_path, asset.url)
        try:
            os.remove(os.path.join(self.parent_path, path))
        except OSError:
            rprint('[yellow]Warning: Could not remove outdated library files.')


class PatchrightInstall:
    '''
    Installs Chromium for Patchright
    '''

    def __init__(self) -> None:
        from patchright._impl._driver import compute_driver_executable, get_driver_env

        self.driver_executable = compute_driver_executable()
        self.env = get_driver_env()

    def execute(self, cmd: str) -> int:
        rprint(f'[bright_yellow]Attempting to {cmd} Patchright Chrome...')
        completed_process = subprocess.run([*self.driver_executable, cmd, 'chromium'], env=self.env)
        rcode: int = completed_process.returncode
        if rcode:
            rprint(f'[red]Failed to {cmd} patchright. Return code: {rcode}')
        return rcode

    def install(self) -> bool:
        return not self.execute('install')

    def uninstall(self) -> bool:
        return not self.execute('uninstall')


HAS_PATCHRIGHT = bool(find_spec('patchright'))
HAS_CAMOUFOX = bool(find_spec('camoufox'))


def panel_msg(text: str) -> None:
    panel = Panel.fit(
        f'[bright_yellow]{text}',
    )
    rprint(panel)


@click.group()
def cli() -> None:
    pass


@cli.command(name='update')
@click.option('--headers', is_flag=True, help='Update headers only')
@click.option('--library', is_flag=True, help='Update library only')
def update(headers=False, library=False):
    '''
    Update all library components
    '''
    # if no options passed, mark both as True
    if not headers ^ library:
        headers = library = True
    library and LibraryUpdate().update()
    if headers:
        rprint('\n[bright_yellow]Downloading BrowserForge headers...')
        Download(headers=True, fingerprints=HAS_PATCHRIGHT or HAS_CAMOUFOX)


@cli.command(name='install')
def install() -> None:
    '''
    Install playwright & all library components
    '''
    # Install hrequests components
    LibraryUpdate().update()

    # Download browserforge headers
    rprint('\n[bright_yellow]Downloading BrowserForge headers...')
    Download(headers=True, fingerprints=HAS_PATCHRIGHT or HAS_CAMOUFOX)
    print('')  # newline to separate

    if not (HAS_PATCHRIGHT or HAS_CAMOUFOX):
        return panel_msg(
            'Please run [white]pip install hrequests\\[all][/] for headless browsing support.',
        )

    # Download the Chrome browser
    if HAS_PATCHRIGHT and PatchrightInstall().install():
        rprint('[green]Chrome browser has been installed!\n')

    # Download Camoufox
    if HAS_CAMOUFOX:
        CamoufoxUpdate().update()
        download_mmdb()


@cli.command(name='uninstall')
@click.option('--camoufox', is_flag=True, help='Uninstall Camoufox browser as well')
@click.option('--patchright', is_flag=True, help='Uninstall Patchright Chrome browser as well')
def uninstall(camoufox: bool, patchright: bool) -> None:
    '''
    Delete all library components
    '''
    path = LibraryUpdate().full_path
    # remove old files
    if not (path and os.path.exists(path)):
        rprint('[bright_yellow]Library components not found.')
    else:
        try:
            os.remove(path)
        except OSError as e:
            rprint(f'[red]WARNING: Could not remove {path}: {e}')
        else:
            rprint(f'[green]Removed {path}')
        rprint('[bright_yellow]Library components have been removed.')

    # Uninstall Camoufox
    if camoufox:
        if HAS_CAMOUFOX:
            # uninstall camoufox components
            if not CamoufoxUpdate().cleanup():
                rprint('[red]Camoufox binaries not found!')
            # Remove the GeoIP database
            remove_mmdb()
        else:
            rprint('[bright_yellow]Camoufox is not installed.')

    # Uninstall Patchright Chrome
    if patchright:
        if HAS_PATCHRIGHT:
            if not PatchrightInstall().uninstall():
                rprint('[red]Patchright Chrome not found!')
        else:
            rprint('[bright_yellow]Patchright is not installed.')

    rprint('[bright_green]Complete! :tada:')


@cli.command(name='version')
def version() -> None:
    '''
    Display the current version of hrequests
    '''
    # python package version
    rprint(f'hrequests:\t[green]{__version__}')

    # library path
    libup = LibraryUpdate()
    path = libup.path
    # if the library is not installed
    if not path:
        rprint('hrequests-cgo:\t[red]Not installed!')
        return
    # library verion
    lib_ver = Version.get_version(path)
    rprint(f'hrequests-cgo:\t[green]{lib_ver}')

    # check for library updates
    with Status('Checking for updates...'):
        latest_ver = libup.latest_asset().version
        if latest_ver == lib_ver:
            rprint('\t\t([yellow]Up to date![/])')
        else:
            rprint(f'\t\t([yellow]latest: {latest_ver}[/])')


if __name__ == '__main__':
    cli()
