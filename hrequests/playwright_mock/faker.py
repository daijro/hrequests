import asyncio
from os.path import dirname, join
import json
from async_class import AsyncObject, link


class Faker(AsyncObject):
    async def __ainit__(self, context, proxy, browser_name, user_agent) -> None:
        link(self, context)
        self.useragent: str = user_agent
        threads = [self.computer(proxy, browser_name), self.locale(proxy)]
        await asyncio.gather(*threads)

    async def computer(self, proxy, browser_name) -> None:
        try:
            url = f"http://fingerprints.bablosoft.com/preview?rand=0.1&tags={browser_name},Desktop,Microsoft%20Windows"
            # Sometimes the API is offline
            while True:
                r = await proxy.httpx.get(url, timeout=20)
                data = r.json()
                # self.useragent = data.get("ua")
                self.vendor: str = data.get("vendor")
                self.renderer: str = data.get("renderer")
                self.width: int = data.get("width", 0)
                self.height: int = data.get("height", 0)
                self.avail_width: int = data.get("availWidth", 0)
                self.avail_height: int = data.get("availHeight", 0)
                # If the Window is too small for the captcha
                if (
                    self.width
                    and self.height > 810
                    and self.avail_height > 810
                    and self.avail_width > 810
                ):
                    return
        except Exception:
            # If Bablosoft Website is offline
            # self.useragent = UserAgent().msie
            self.vendor: str = "Google Inc."
            self.renderer: str = "Google Inc. (AMD)"
            self.width: int = 1280
            self.height: int = 720
            self.avail_width: int = 1280
            self.avail_height: int = 720

    async def locale(self, proxy) -> None:
        with open(join(dirname(__file__), "locale.json"), "r") as f:
            language_dict = json.load(f)

        country_code = proxy.country_code

        if country_code in language_dict:
            self.locale, self.language_code = language_dict[country_code]
        else:
            raise ValueError("Proxy Country not supported")
