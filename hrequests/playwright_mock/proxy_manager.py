import contextlib
import re
from typing import Dict, Optional

import httpx
from async_class import AsyncObject, link


class SplitError(Exception):
    pass


class ProxyCheckError(Exception):
    pass


class ProxyManager(AsyncObject):
    proxy: str = ""
    http_proxy: Dict[str, str] = {}
    browser_proxy: Optional[Dict[str, str]] = None
    plain_proxy: str = ""
    _httpx: httpx.AsyncClient
    _phttpx: httpx.AsyncClient
    ip: Optional[str] = None
    port: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    timezone: Optional[str] = None

    async def __ainit__(self, botright, proxy: str) -> None:
        """
        Initialize a ProxyManager instance with a proxy string and perform proxy checks.

        Args:
            botright: An instance of Botright for linking purposes.
            proxy (str): The proxy string to be managed and checked.
        """
        link(self, botright)

        self.proxy = proxy

        self.timeout = httpx.Timeout(20.0, read=None)
        self._httpx = httpx.AsyncClient()

        if self.proxy:
            self.split_proxy()
            self.proxy = (
                f"{self.username}:{self.password}@{self.ip}:{self.port}"
                if self.username
                else f"{self.ip}:{self.port}"
            )
            self.plain_proxy = f"{self.schema}://{self.proxy}"
            self._phttpx = httpx.AsyncClient(proxies={"all://": self.plain_proxy}, verify=False)

            if self.username:
                self.browser_proxy = {
                    "server": f"{self.ip}:{self.port}",
                    "username": self.username,
                    "password": self.password,
                }
            else:
                self.browser_proxy = {"server": self.plain_proxy}

        else:
            self._phttpx = self._httpx

        await self.check_proxy(self._phttpx)

    async def __adel__(self) -> None:
        await self._httpx.aclose()
        await self._phttpx.aclose()

    proxy_reg: re.Pattern = re.compile(
        '^(?P<schema>\w+)://'
        '(?:'
        '(?P<user>[^\:]+):'
        '(?P<password>[^@]+)@)?'
        '(?P<ip>.*?)'
        '(?:\:'
        '(?P<port>\d+))?$'
    )

    def split_proxy(self) -> None:
        match = self.proxy_reg.match(self.proxy)
        self.schema = match['schema']
        self.username = match['user']
        self.password = match['password']
        self.ip = match['ip']
        self.port = match['port']

    async def check_proxy(self, httpx_client: httpx.AsyncClient) -> None:
        """
        Check the validity of the proxy by making HTTP requests to determine its properties.

        Args:
            httpx_client (httpx.AsyncClient): The HTTPX client to use for proxy checks.
        """
        get_ip_apis = [
            "https://api.ipify.org/?format=json",
            "https://api.myip.com/",
            "https://get.geojs.io/v1/ip.json",
            "https://api.ip.sb/jsonip",
            "https://l2.io/ip.json",
        ]

        for get_ip_api in get_ip_apis:
            with contextlib.suppress(Exception):
                ip_request = await httpx_client.get(get_ip_api, timeout=self.timeout)
                ip = ip_request.json().get("ip")
                break
        else:
            raise ProxyCheckError("Could not get IP-Address of Proxy (Proxy is Invalid/Timed Out)")

        get_geo_apis = {
            "http://ip-api.com/json/{IP}": ("country", "countryCode", "lat", "lon", "timezone"),
            "https://ipapi.co/{IP}/json": (
                "country_name",
                "country",
                "latitude",
                "longitude",
                "timezone",
            ),
            "https://api.techniknews.net/ipgeo/{IP}": (
                "country",
                "countryCode",
                "lat",
                "lon",
                "timezone",
            ),
            "https://get.geojs.io/v1/ip/geo/{IP}.json": (
                "country",
                "country_code",
                "latitude",
                "longitude",
                "timezone",
            ),
        }

        for get_geo_api, api_names in get_geo_apis.items():
            with contextlib.suppress(Exception):
                api_url = get_geo_api.format(IP=ip)
                country, country_code, latitude, longitude, timezone = api_names
                r = await self._httpx.get(api_url, timeout=self.timeout)
                data = r.json()

                self.country = data.get(country)
                self.country_code = data.get(country_code)
                self.latitude = data.get(latitude)
                self.longitude = data.get(longitude)
                self.timezone = data.get(timezone)

                assert self.country
                break
        else:
            raise ProxyCheckError(
                "Could not get GeoInformation from proxy (Proxy is probably not Indexed)"
            )
