import ctypes
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode

from orjson import dumps, loads

import hrequests

from .cffi import freeMemory, request
from .cookies import (
    RequestsCookieJar,
    cookiejar_from_dict,
    cookiejar_to_list,
    extract_cookies_to_jar,
    list_to_cookiejar,
    merge_cookies,
)
from .exceptions import ClientException
from .toolbelt import CaseInsensitiveDict

try:
    import turbob64 as base64
except ImportError:
    import base64

'''
TLSClient heavily based on https://github.com/FlorianREGAZ/Python-Tls-Client
Copyright (c) 2022 Florian Zager
'''


@dataclass
class TLSClient:
    client_identifier: Optional[str] = None
    random_tls_extension_order: bool = True
    force_http1: bool = False
    catch_panics: bool = False
    debug: bool = False
    proxies: Optional[dict] = None
    cookies: Optional[RequestsCookieJar] = None

    # custom TLS profile
    ja3_string: Optional[str] = None
    h2_settings: Optional[Dict[str, int]] = None
    h2_settings_order: Optional[List[str]] = None
    supported_signature_algorithms: Optional[List[str]] = None
    supported_delegated_credentials_algorithms: Optional[List[str]] = None
    supported_versions: Optional[List[str]] = None
    key_share_curves: Optional[List[str]] = None
    cert_compression_algo: Optional[str] = None
    additional_decode: Optional[str] = None
    pseudo_header_order: Optional[List[str]] = None
    connection_flow: Optional[int] = None
    priority_frames: Optional[list] = None
    header_order: Optional[List[str]] = None
    header_priority: Optional[List[str]] = None

    '''
    Synopsis:
    
    self.client_identifier examples:
    - Chrome > chrome_103, chrome_104, chrome_105, chrome_106
    - Firefox > firefox_102, firefox_104
    - Opera > opera_89, opera_90
    - Safari > safari_15_3, safari_15_6_1, safari_16_0
    - iOS > safari_ios_15_5, safari_ios_15_6, safari_ios_16_0
    - iPadOS > safari_ios_15_6

    self.ja3_string example:
    - 771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0

    HTTP2 Header Frame Settings
    - HEADER_TABLE_SIZE
    - SETTINGS_ENABLE_PUSH
    - MAX_CONCURRENT_STREAMS
    - INITIAL_WINDOW_SIZE
    - MAX_FRAME_SIZE
    - MAX_HEADER_LIST_SIZE

    self.h2_settings example:
    {
        "HEADER_TABLE_SIZE": 65536,
        "MAX_CONCURRENT_STREAMS": 1000,
        "INITIAL_WINDOW_SIZE": 6291456,
        "MAX_HEADER_LIST_SIZE": 262144
    }

    HTTP2 Header Frame Settings Order
    self.h2_settings_order example:
    [
        "HEADER_TABLE_SIZE",
        "MAX_CONCURRENT_STREAMS",
        "INITIAL_WINDOW_SIZE",
        "MAX_HEADER_LIST_SIZE"
    ]

    Supported Signature Algorithms
    - PKCS1WithSHA256
    - PKCS1WithSHA384
    - PKCS1WithSHA512
    - PSSWithSHA256
    - PSSWithSHA384
    - PSSWithSHA512
    - ECDSAWithP256AndSHA256
    - ECDSAWithP384AndSHA384
    - ECDSAWithP521AndSHA512
    - PKCS1WithSHA1
    - ECDSAWithSHA1

    self.supported_signature_algorithms example:
    [
        "ECDSAWithP256AndSHA256",
        "PSSWithSHA256",
        "PKCS1WithSHA256",
        "ECDSAWithP384AndSHA384",
        "PSSWithSHA384",
        "PKCS1WithSHA384",
        "PSSWithSHA512",
        "PKCS1WithSHA512",
    ]

    Supported Delegated Credentials Algorithms
    - PKCS1WithSHA256
    - PKCS1WithSHA384
    - PKCS1WithSHA512
    - PSSWithSHA256
    - PSSWithSHA384
    - PSSWithSHA512
    - ECDSAWithP256AndSHA256
    - ECDSAWithP384AndSHA384
    - ECDSAWithP521AndSHA512
    - PKCS1WithSHA1
    - ECDSAWithSHA1

    self.supported_delegated_credentials_algorithms example:
    [
        "ECDSAWithP256AndSHA256",
        "PSSWithSHA256",
        "PKCS1WithSHA256",
        "ECDSAWithP384AndSHA384",
        "PSSWithSHA384",
        "PKCS1WithSHA384",
        "PSSWithSHA512",
        "PKCS1WithSHA512",
    ]

    Supported Versions
    - GREASE
    - 1.3
    - 1.2
    - 1.1
    - 1.0

    self.supported_versions example:
    [
        "GREASE",
        "1.3",
        "1.2"
    ]

    Key Share Curves
    - GREASE
    - P256
    - P384
    - P521
    - X25519

    self.key_share_curves example:
    [
        "GREASE",
        "X25519"
    ]

    Cert Compression Algorithm
    self.cert_compression_algo examples: "zlib", "brotli", "zstd"

    Additional Decode
    Make sure the go code decodes the response body once explicit by provided algorithm.
    self.additional_decode examples: null, "gzip", "br", "deflate"

    Pseudo Header Order (:authority, :method, :path, :scheme)
    self.pseudo_header_order examples:
    [
        ":method",
        ":authority",
        ":scheme",
        ":path"
    ]

    Connection Flow / Window Size Increment
    self.connection_flow example:
    15663105

    self.priority_frames example:
    [
        {
        "streamID": 3,
        "priorityParam": {
            "weight": 201,
            "streamDep": 0,
            "exclusive": false
        }
        },
        {
        "streamID": 5,
        "priorityParam": {
            "weight": 101,
            "streamDep": false,
            "exclusive": 0
        }
        }
    ]

    Order of your headers
    self.header_order example:
    [
        "key1",
        "key2"
    ]

    Header Priority
    self.header_priority example:
    {
        "streamDep": 1,
        "exclusive": true,
        "weight": 1
    }
    
    Proxies
    self.proxies usage:
    {
        "http": "http://user:pass@ip:port",
        "https": "http://user:pass@ip:port"
    }
    '''

    def __post_init__(self) -> None:
        self._session_id: str = str(uuid.uuid4())

        self.headers: CaseInsensitiveDict = CaseInsensitiveDict()
        self.proxies: dict = self.proxies or {}

        # CookieJar containing all currently outstanding cookies set on this session
        self.cookies: RequestsCookieJar = self.cookies or RequestsCookieJar()

    def execute_request(
        self,
        method: str,
        url: str,
        data: Optional[Union[str, bytes, bytearray, dict]] = None,
        headers: Optional[Union[dict, CaseInsensitiveDict]] = None,
        cookies: Optional[Union[RequestsCookieJar, dict, list]] = None,
        json: Optional[Union[dict, list, str]] = None,
        allow_redirects: bool = False,
        verify: Optional[bool] = None,
        timeout: Optional[float] = None,
        proxy: Optional[dict] = None,
    ):
        # Prepare request body - build request body
        # Data has priority. JSON is only used if data is None.
        if data is None and json is not None:
            if type(json) in (dict, list):
                json = dumps(json).decode('utf-8')
            request_body = json
            content_type = 'application/json'
        elif data is not None and type(data) not in (str, bytes):
            request_body = urlencode(data, doseq=True)
            content_type = 'application/x-www-form-urlencoded'
        else:
            request_body = data
            content_type = None
        # set content type if it isn't set
        if content_type is not None and 'content-type' not in self.headers:
            self.headers['Content-Type'] = content_type

        # Prepare Headers
        if self.headers is None:
            headers = CaseInsensitiveDict(headers)
        elif headers is None:
            headers = self.headers
        else:
            merged_headers = CaseInsensitiveDict(self.headers)
            merged_headers.update(headers)

            # Remove items, where the key or value is set to None.
            none_keys = [k for (k, v) in merged_headers.items() if v is None or k is None]
            for key in none_keys:
                del merged_headers[key]

            headers = merged_headers

        # Cookies
        if isinstance(cookies, RequestsCookieJar):
            merge_cookies(self.cookies, cookies)
        elif isinstance(cookies, list):
            merge_cookies(self.cookies, list_to_cookiejar(cookies))
        elif isinstance(cookies, dict):
            self.cookies.set_cookie(cookiejar_from_dict(cookies))

        # turn cookie jar into dict

        # Proxy
        proxy = proxy or self.proxies

        if type(proxy) is dict and 'http' in proxy:
            proxy = proxy['http']
        elif type(proxy) is str:
            proxy = proxy
        else:
            proxy = ''

        # Request
        is_byte_request = isinstance(request_body, (bytes, bytearray))
        request_payload = {
            'sessionId': self._session_id,
            'followRedirects': allow_redirects,
            'forceHttp1': self.force_http1,
            'withDebug': self.debug,
            'catchPanics': self.catch_panics,
            'headers': dict(headers) if isinstance(headers, CaseInsensitiveDict) else headers,
            'headerOrder': self.header_order,
            'insecureSkipVerify': not verify,
            'isByteRequest': is_byte_request,
            'additionalDecode': self.additional_decode,
            'proxyUrl': proxy,
            'requestUrl': url,
            'requestMethod': method,
            'requestBody': base64.b64encode(request_body).decode()
            if is_byte_request
            else request_body,
            'requestCookies': cookiejar_to_list(self.cookies),
            'timeoutMilliseconds': int(timeout * 1000),
        }
        if self.client_identifier is None:
            request_payload['customTlsClient'] = {
                'ja3String': self.ja3_string,
                'h2Settings': self.h2_settings,
                'h2SettingsOrder': self.h2_settings_order,
                'pseudoHeaderOrder': self.pseudo_header_order,
                'connectionFlow': self.connection_flow,
                'priorityFrames': self.priority_frames,
                'headerPriority': self.header_priority,
                'certCompressionAlgo': self.cert_compression_algo,
                'supportedVersions': self.supported_versions,
                'supportedSignatureAlgorithms': self.supported_signature_algorithms,
                'supportedDelegatedCredentialsAlgorithms': self.supported_delegated_credentials_algorithms,
                'keyShareCurves': self.key_share_curves,
            }
        else:
            request_payload['tlsClientIdentifier'] = self.client_identifier
            request_payload['withRandomTLSExtensionOrder'] = self.random_tls_extension_order

        # this is a pointer to the response
        response = request(dumps(request_payload))
        # dereference the pointer to a byte array
        # convert response string to json
        response_object = loads(ctypes.string_at(response))
        # free the memory
        freeMemory(response_object['id'].encode('utf-8'))

        # Error handling
        if response_object['status'] == 0:
            raise ClientException(response_object['body'])

        # Set response cookies
        response_cookie_jar = extract_cookies_to_jar(
            request_url=url,
            request_headers=headers,
            cookie_jar=self.cookies,
            response_headers=response_object['headers'],
        )
        # build response class
        return hrequests.response.build_response(response_object, response_cookie_jar)
