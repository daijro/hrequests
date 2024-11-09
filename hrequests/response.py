import base64
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from http.client import responses as status_codes
from typing import Callable, List, Literal, Optional, Union

import cchardet as chardet
from orjson import dumps, loads

import hrequests
from hrequests.cffi import library
from hrequests.exceptions import ClientException
from hrequests.proxies import BaseProxy

from .cookies import RequestsCookieJar
from .toolbelt import CaseInsensitiveDict, FileUtils


class ProcessResponse:
    def __init__(
        self,
        session,
        method: str,
        url: str,
        files: Optional[dict] = None,
        cookies: Optional[Union[RequestsCookieJar, dict, list]] = None,
        **kwargs,
    ) -> None:
        self.session: 'hrequests.session.TLSSession' = session
        self.method: str = method
        self.url: str = url

        if files:
            data = kwargs['data']
            headers = kwargs['headers']
            # assert that data is a dict
            if data is not None:
                assert isinstance(data, dict), "Data must be a dict when files are passed"
            # convert files to multipart/form-data
            kwargs['data'], content_type = FileUtils.encode_files(files, data)
            # content_type needs to be set to Content-Type header
            if headers is None:
                headers = {}
            # else if headers were provided, append Content-Type to those
            elif isinstance(headers, dict):
                headers = CaseInsensitiveDict(headers)
            headers['Content-Type'] = content_type
            kwargs['headers'] = headers

        self.cookies: Optional[Union[RequestsCookieJar, dict, list]] = cookies
        self.kwargs: dict = kwargs
        self.response: Response

    def send(self) -> None:
        time: datetime = datetime.now()
        self.response = self.execute_request()
        self.response.elapsed = datetime.now() - time

    def execute_request(self) -> 'Response':
        try:
            resp = self.session.execute_request(
                method=self.method,
                url=self.url,
                cookies=self.cookies,
                **self.kwargs,
            )
        except ClientException as e:
            raise e
        except IOError as e:
            raise ClientException('Connection error') from e
        # Set internal data from the session
        resp.session = None if self.session.temp else self.session
        # Set browser data for rendering
        resp.browser = self.session.browser
        resp.version = self.session.version
        return resp


class ProcessResponsePool:
    '''
    Processes a pool of ProcessResponse objects
    '''

    def __init__(self, pool: List[ProcessResponse]) -> None:
        self.pool: List[ProcessResponse] = pool

    def execute_pool(self) -> List['Response']:
        values: list = []
        for proc in self.pool:
            # get the request data
            payload, headers = proc.session.build_request(
                method=proc.method,
                url=proc.url,
                cookies=proc.cookies,
                **proc.kwargs,
            )
            # remember full set of headers (including from session)
            proc.full_headers = headers
            # add to values
            values.append(payload)
        # execute the pool
        try:
            # send request
            resp = proc.session.server.post(
                f'http://127.0.0.1:{library.PORT}/multirequest', body=dumps(values)
            )
            response_object = loads(resp.read())
        except Exception as e:
            raise ClientException('Connection error') from e
        # process responses
        return [
            proc.session.build_response(proc.url, proc.full_headers, data, payload['proxyUrl'])
            for proc, data in zip(self.pool, response_object)
        ]


@dataclass
class Response:
    """
    Response object

    Methods:
        json: Returns the response body as json
        render: Renders the response body with BrowserSession
        find: Shortcut to .html.find

    Attributes:
        url (str): Response url
        status_code (int): Response status code
        reason (str): Response status reason
        headers (CaseInsensitiveDict): Response headers
        cookies (RequestsCookieJar): Response cookies
        text (str): Response body as text
        content (Union[str, bytes]): Response body as bytes or str
        ok (bool): True if status code is less than 400
        elapsed (datetime.timedelta): Time elapsed between sending the request and receiving the response
        html (hrequests.parser.HTML): Response body as HTML parser object
    """

    url: str
    status_code: int
    headers: 'hrequests.client.CaseInsensitiveDict'
    cookies: RequestsCookieJar
    raw: Union[str, bytes] = None

    # set by ProcessResponse
    history: Optional[List['Response']] = None
    session: Optional[Union['hrequests.session.TLSSession', 'hrequests.browser.BrowserSession']] = (
        None
    )
    browser: Literal['firefox', 'chrome'] = None
    version: Optional[int] = None
    elapsed: Optional[timedelta] = None
    encoding: str = 'UTF-8'
    is_utf8: bool = True
    proxy: Optional[str] = None

    def __post_init__(self) -> None:
        if type(self.raw) is bytes:
            self.encoding = chardet.detect(self.raw)['encoding']

    @property
    def reason(self) -> str:
        return status_codes[self.status_code]

    def json(self, **kwargs) -> Union[dict, list]:
        return loads(self.content, **kwargs)

    @property
    def content(self) -> bytes:
        # note: this will convert the content to bytes on each access
        return self.raw if type(self.raw) is bytes else self.raw.encode(self.encoding)

    @property
    def text(self) -> str:
        return self.raw if type(self.raw) is str else self.raw.decode(self.encoding)

    @property
    def html(self) -> 'hrequests.parser.HTML':
        if not self.__dict__.get('_html'):
            self._html = hrequests.parser.HTML(
                session=self.session, url=self.url, html=self.content
            )
        return self._html

    @property
    def find(self) -> Callable:
        return self.html.find

    @property
    def find_all(self) -> Callable:
        return self.html.find_all

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    @property
    def links(self) -> dict:
        '''Returns the parsed header links of the response, if any'''
        header = self.headers.get("link")
        resolved_links = {}

        if not header:
            return resolved_links

        links = parse_header_links(header)
        for link in links:
            key = link.get("rel") or link.get("url")
            resolved_links[key] = link
        return resolved_links

    def __bool__(self) -> bool:
        '''Returns True if :attr:`status_code` is less than 400'''
        return self.ok

    def render(
        self,
        *,
        proxy: Optional[Union[str, BaseProxy]] = None,
        browser: Optional[Literal['firefox', 'chrome']] = None,
        **kwargs,
    ) -> 'hrequests.browser.BrowserSession':
        return hrequests.browser.render(
            url=self.url,  # Enable CORS requests during render: #56
            response=self,
            session=self.session,
            proxy=proxy or self.proxy,
            version=self.version,
            browser=browser or self.browser,
            **kwargs,
        )

    def __enter__(self):
        return self

    def __repr__(self):
        return f"<Response [{self.status_code}]>"


def parse_header_links(value):
    '''
    Return a list of parsed link headers proxies.
    i.e. Link: <http:/.../front.jpeg>; rel=front; type="image/jpeg",<http://.../back.jpeg>; rel=back;type="image/jpeg"
    :rtype: list
    '''
    links = []
    replace_chars = " '\""
    value = value.strip(replace_chars)

    if not value:
        return links

    for val in re.split(", *<", value):
        try:
            url, params = val.split(";", 1)
        except ValueError:
            url, params = val, ""
        link = {"url": url.strip("<> '\"")}
        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break
            link[key.strip(replace_chars)] = value.strip(replace_chars)
        links.append(link)
    return links


def build_response(
    res: Union[dict, list], res_cookies: RequestsCookieJar, proxy: Optional[str]
) -> Response:
    '''Builds a Response object'''
    # build headers
    if res["headers"] is None:
        res_headers = {}
    else:
        res_headers = {
            header_key: header_value[0] if len(header_value) == 1 else header_value
            for header_key, header_value in res["headers"].items()
        }
    # decode bytes response
    if res.get('isBase64'):
        res['body'] = base64.b64decode(res['body'].encode())
    return Response(
        # add target / url
        url=res["target"],
        # add status code
        status_code=res["status"],
        # add headers
        headers=hrequests.client.CaseInsensitiveDict(res_headers),
        # add cookies
        cookies=res_cookies,
        # add response body
        raw=res["body"],
        # if response was utf-8 validated
        is_utf8=not res.get('isBase64'),
        # add proxy
        proxy=proxy,
    )
