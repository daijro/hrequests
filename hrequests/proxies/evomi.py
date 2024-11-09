import random
import string
from typing import Literal, Optional

from hrequests.proxies.mixin import BaseProxy


class EvomiProxy(BaseProxy):
    """
    Proxies provided by the Evomi service.
    """

    def __init__(
        self,
        username: str,
        key: str,
        country: Optional[str] = None,
        region: Optional[str] = None,
        city: Optional[str] = None,
        continent: Optional[str] = None,
        isp: Optional[str] = None,
        pool: Optional[Literal["standard", "speed", "quality"]] = None,
        session_type: Literal["session", "hardsession"] = "session",
        auto_rotate: bool = False,
        lifetime: Optional[int] = None,
        adblock: bool = False,
    ):
        # Confirm that lifetime is not provided for hardsession
        if session_type == "hardsession" and lifetime is not None:
            raise ValueError("lifetime cannot be provided for hardsession")
        # Confirm that lifetime is not greater than 120
        if lifetime and lifetime > 120:
            raise ValueError("lifetime must be less than 120")
        # Confirm that lifetime is not provided for auto_rotate
        if auto_rotate and lifetime is not None:
            raise ValueError("lifetime cannot be provided for auto-rotate")

        self._auto_rotate = auto_rotate

        self._data = {
            "continent": _to_proxy_fmt(continent),
            "city": _to_proxy_fmt(city),
            "region": _to_proxy_fmt(region),
            "country": country,
            "isp": isp,
            "pool": pool,
            "lifetime": lifetime,
            "adblock": 1 if adblock else None,
            session_type: None if auto_rotate else self._random_id(),
        }

        self.kwargs = {
            "username": username,
            "key": key,
            "data": self._wrap_data(**self._data),
        }

    def rotate(self):
        """
        Rotates the proxy. Works only if not auto-rotating.
        """
        if self._auto_rotate:
            raise ValueError("Cannot rotate an already auto-rotating proxy.")

        self._data["session_type"] = self._random_id()
        self.kwargs["data"] = self._wrap_data(**self._data)

    @staticmethod
    def _random_id() -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=10))  # nosec

    """
    Generates strings to append to the URLs
    """

    @staticmethod
    def _wrap_data(**kwargs) -> str:
        data = ""
        for key, value in kwargs.items():
            if value is not None:
                data += f"_{key}-{value}"
        return data


class ResidentialProxy(EvomiProxy):
    URL = "http://{username}:{key}{data}@rp.evomi.com:1000"
    SERVICE = "Evomi Residential"

    def __init__(
        self,
        username: str,
        key: str,
        country: Optional[str] = None,
        region: Optional[str] = None,
        city: Optional[str] = None,
        continent: Optional[str] = None,
        isp: Optional[str] = None,
        pool: Optional[Literal["standard", "speed", "quality"]] = None,
        session_type: Literal["session", "hardsession"] = "session",
        auto_rotate: bool = False,
        lifetime: Optional[int] = None,
        adblock: bool = False,
    ):
        """
        Initialize a new Evomi Residential proxy.

        Parameters:
            username (str): Your Evomi username
            key (str): Your Evomi API key
            country (str, optional): Target country code (e.g., 'US', 'GB')
            region (str, optional): Target region/state
            city (str, optional): Target city name
            continent (str, optional): Target continent name
            isp (str, optional): Target ISP
            pool (Literal["standard", "speed", "quality"], optional): Proxy pool type
            session_type (Literal["session", "hardsession"]): Session persistence type
                * "session": Optimized for success rate, may change IP for stability. Works with lifetime parameter.
                * "hardsession": Maintains same IP for as long as possible. Cannot use lifetime parameter.
                Defaults to "session".
            auto_rotate (bool): Whether to automatically rotate IPs between requests.
                Cannot be used with `session_type`.
            lifetime (int, optional): Duration of the session in minutes (1-120)
                Only works with `session_type="session"`. Defaults to 40 if not specified.
            adblock (bool): Whether to enable ad blocking. Defaults to False.
        """
        super().__init__(
            username=username,
            key=key,
            country=country,
            region=region,
            city=city,
            continent=continent,
            isp=isp,
            pool=pool,
            session_type=session_type,
            auto_rotate=auto_rotate,
            lifetime=lifetime,
            adblock=adblock,
        )


class MobileProxy(EvomiProxy):
    URL = "http://{username}:{key}{data}@mp.evomi.com:3000"
    SERVICE = "Evomi Mobile"

    def __init__(
        self,
        username: str,
        key: str,
        country: Optional[str] = None,
        region: Optional[str] = None,
        continent: Optional[str] = None,
        isp: Optional[str] = None,
        session_type: Literal["session", "hardsession"] = "session",
        auto_rotate: bool = False,
        lifetime: Optional[int] = None,
    ):
        """
        Initialize a new Evomi Mobile proxy.

        Parameters:
            username (str): Your Evomi username
            key (str): Your Evomi API key
            country (str, optional): Target country code (e.g., 'US', 'GB')
            continent (str, optional): Target continent name
            isp (str, optional): Target ISP
            session_type (Literal["session", "hardsession"]): Session persistence type
                * "session": Optimized for success rate, may change IP for stability. Works with lifetime parameter.
                * "hardsession": Maintains same IP for as long as possible. Cannot use lifetime parameter.
                Defaults to "session".
            auto_rotate (bool): Whether to automatically rotate IPs between requests.
                Cannot be used with `session_type`.
            lifetime (int, optional): Duration of the session in minutes (1-120)
                Only works with `session_type="session"`. Defaults to 40 if not specified.
        """
        super().__init__(
            username=username,
            key=key,
            country=country,
            region=region,
            continent=continent,
            isp=isp,
            session_type=session_type,
            auto_rotate=auto_rotate,
            lifetime=lifetime,
        )


class DatacenterProxy(EvomiProxy):
    URL = "http://{username}:{key}{data}@dcp.evomi.com:2000"
    SERVICE = "Evomi Datacenter"

    def __init__(
        self,
        username: str,
        key: str,
        country: Optional[str] = None,
        continent: Optional[str] = None,
        session_type: Literal["session", "hardsession"] = "session",
        auto_rotate: bool = False,
        lifetime: Optional[int] = None,
    ):
        """
        Initialize a new Evomi Datacenter proxy.

        Parameters:
            username (str): Your Evomi username
            key (str): Your Evomi API key
            country (str, optional): Target country code (e.g., 'US', 'GB')
            continent (str, optional): Target continent name
            session_type (Literal["session", "hardsession"]): Session persistence type
                * "session": Optimized for success rate, may change IP for stability. Works with lifetime parameter.
                * "hardsession": Maintains same IP for as long as possible. Cannot use lifetime parameter.
                Defaults to "session".
            auto_rotate (bool): Whether to automatically rotate IPs between requests.
                Cannot be used with `session_type`.
            lifetime (int, optional): Duration of the session in minutes (1-120)
                Only works with `session_type="session"`. Defaults to 40 if not specified.
        """
        super().__init__(
            username=username,
            key=key,
            country=country,
            continent=continent,
            session_type=session_type,
            auto_rotate=auto_rotate,
            lifetime=lifetime,
        )


def _to_proxy_fmt(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    # Replaces "New York" with "new.york"
    return '.'.join(s.lower().split())
