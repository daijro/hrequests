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
        city: Optional[str] = None,
        region: Optional[str] = None,
        isp: Optional[str] = None,
        asn: Optional[str] = None,
        continent: Optional[str] = None,
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
            "country": country,
            "city": city,
            "region": region,
            "isp": isp,
            "asn": asn,
            "continent": continent,
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


class DatacenterProxy(EvomiProxy):
    URL = "http://{username}:{key}{data}@dcp.evomi.com:2000"
    SERVICE = "Evomi Datacenter"


class MobileProxy(EvomiProxy):
    URL = "http://{username}:{key}{data}@mp.evomi.com:3000"
    SERVICE = "Evomi Mobile"
