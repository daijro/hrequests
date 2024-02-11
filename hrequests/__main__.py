import os
import re
import subprocess
import sys
from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path
from typing import Optional

import click
from rich import print as rprint
from rich.panel import Panel
from rich.status import Status

from hrequests.__version__ import BRIDGE_VERSION, __version__
from hrequests.cffi import LibraryManager, root_dir
from hrequests.headers import ChromeVersions, FirefoxVersions

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
            '\nSee the documentation to get started: https://daijro.gitbook.io/hrequests\n'
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
            rprint(f'Current version: [green]v{current_ver}\n')
            return

        # download updated file
        rprint(f'Updating hrequests-cgo library from [red]v{current_ver}[/] => v{asset.version}')
        # download new, remove old
        self.download_file(self.full_path, asset.url)
        try:
            os.remove(os.path.join(self.parent_path, path))
        except OSError:
            rprint('[yellow]Warning: Could not remove outdated library files.')


class HeaderUpdate:
    def update(self) -> None:
        '''
        Updates the saved header versions
        '''
        ChromeVersions(force_dl=True)
        FirefoxVersions(force_dl=True)


class PlaywrightInstall:
    '''
    Installs playwright browsers
    '''

    def __init__(self) -> None:
        from playwright._impl._driver import compute_driver_executable, get_driver_env

        self.driver_executable = compute_driver_executable()
        self.env = get_driver_env()

    def execute(self, cmd: str) -> int:
        completed_process = subprocess.run(
            [str(self.driver_executable), cmd, 'firefox', 'chromium'], env=self.env
        )
        rcode: int = completed_process.returncode
        if rcode:
            rprint(f'[red]Failed to {cmd} playwright. Return code: {rcode}')
        return rcode

    def install(self) -> bool:
        return not self.execute('install')

    def uninstall(self) -> bool:
        rcode: int = self.execute('uninstall')
        if rcode == 1:
            rprint(
                '[yellow]WARNING: On older versions of playwright, the `uninstall` command does not work.\n'
                f'To manually uninstall, remove the cache from here: {self.browser_binaries()}'
            )
        return not rcode

    @staticmethod
    def browser_binaries() -> str:
        r'''
        Return the path to playwright browser binaries based on OS

        %USERPROFILE%\AppData\Local\ms-playwright on Windows
        ~/Library/Caches/ms-playwright on MacOS
        ~/.cache/ms-playwright on Linux
        '''
        if sys.platform == 'win32':
            return os.path.expandvars('%USERPROFILE%\\AppData\\Local\\ms-playwright')
        if sys.platform == 'darwin':
            return os.path.expanduser('~/Library/Caches/ms-playwright')
        return os.path.expanduser('~/.cache/ms-playwright')

    @staticmethod
    def exists() -> bool:
        return 'playwright' in sys.modules


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
    headers and HeaderUpdate().update()


@cli.command(name='install')
def install() -> None:
    '''
    Install playwright & all library components
    '''
    if PlaywrightInstall.exists():
        if PlaywrightInstall().install():
            rprint('[green]Playwright browsers are installed!\n')
    else:
        panel = Panel.fit(
            '[bright_yellow]Please run [white]pip install hrequests\\[all][/] for headless browsing support.',
        )
        rprint(panel)
    # install hrequests components
    LibraryUpdate().update()
    HeaderUpdate().update()


@cli.command(name='uninstall')
@click.option('--playwright', is_flag=True, help='Uninstall playwright as well')
def uninstall(playwright: bool) -> None:
    '''
    Delete all library components
    '''
    for path in (
        ChromeVersions.file_name,
        FirefoxVersions.file_name,
        LibraryUpdate().full_path,
    ):
        # remove old files
        if not (path and os.path.exists(path)):
            continue
        try:
            os.remove(path)
        except OSError as e:
            rprint(f'[red]WARNING: Could not remove {path}: {e}')
        else:
            rprint(f'[green]Removed {path}')
    rprint('[bright_yellow]Library components have been removed.')

    if not playwright:
        return
    # check if playwright is installed
    if not PlaywrightInstall.exists():
        rprint('[bright_yellow]Playwright is not installed.')
        return
    # uninstall playwright
    if PlaywrightInstall().uninstall():
        rprint('[green]Successfully removed Firefox and Chromium profiles!')


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
            rprint(f'\t\t([yellow]latest = {latest_ver}[/])')


if __name__ == '__main__':
    cli()
