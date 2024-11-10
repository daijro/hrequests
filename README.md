<img src="https://i.imgur.com/r8GcQW1.png" align="center">
</img>

<h2 align="center">hrequests</h2>

<h4 align="center">
<p align="center">
    <a href="https://github.com/daijro/hrequests/blob/main/LICENSE">
        <img src="https://img.shields.io/github/license/daijro/hrequests.svg">
    </a>
    <a href="https://python.org/">
        <img src="https://img.shields.io/badge/python-3.8&#8208;3.13-blue">
    </a>
    <a href="https://pypi.org/project/hrequests/">
        <img alt="PyPI" src="https://img.shields.io/pypi/v/hrequests.svg">
    </a>
    <a href="https://github.com/daijro/hrequests/releases">
        <img alt="downloads" src="https://img.shields.io/github/downloads/daijro/hrequests/total.svg?label=downloads">
    </a>
    <a href="https://pepy.tech/project/hrequests">
        <img alt="PyPI" src="https://img.shields.io/pepy/dt/hrequests?label=pypi installs&color=blue">
    </a>
    <a href="https://github.com/ambv/black">
        <img src="https://img.shields.io/badge/code%20style-black-black.svg">
    </a>
    <a href="https://github.com/PyCQA/isort">
        <img src="https://img.shields.io/badge/imports-isort-yellow.svg">
    </a>
</p>
    Hrequests (human requests) is a simple, configurable, feature-rich, replacement for the Python requests library. 
</h4>

### ✨ Features

- Seamless transition between HTTP and headless browsing 💻
- Integrated fast HTML parser 🚀
- High performance network concurrency with goroutines & gevent 🚀
- Replication of browser TLS fingerprints 🚀
- JavaScript rendering 🚀
- Supports HTTP/2 🚀
- Realistic browser header generation using [BrowserForge](https://github.com/daijro/browserforge) 🚀
- JSON serializing up to 10x faster than the standard library 🚀

### 💻 Browser crawling

- Simple & uncomplicated browser automation
- Anti-detect browsing using [Camoufox](https://camoufox.com) and [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) (**new in v0.9.0!**)
- Human-like cursor movement and typing
- Full page screenshots
- Proxy support
- Headless and headful support
- No CORS restrictions

### ⚡ More

- High performance ✨
- HTTP backend written in Go
- Automatic gzip & brotli decode
- Written with type safety
- 100% threadsafe ❤️

---

### 🏠 Residential Proxy Rotation ($0.49 per GB)

Hrequests includes built-in proxy rotation powered by [Evomi](https://evomi.com?utm_source=github&utm_medium=banner&utm_campaign=daijro-hrequests). 🚀

[Evomi](https://evomi.com?utm_source=github&utm_medium=banner&utm_campaign=daijro-hrequests) is a high quality Swiss proxy provider, with residential proxies avaliable in 150+ countries starting at $0.49/GB. For more information on using Evomi in hrequests, see the [Evomi proxy guide](#evomi-proxies).

- 👩‍💻 **24/7 Expert Support**: Evomi will join your Slack Channel
- 🌍 **Global Presence**: Available in 150+ Countries
- ⚡ **Low Latency**
- 🔒 **Swiss Quality & Privacy**
- 🎁 **Free Trial**
- 🛡️ **99.9% Uptime**
- 🤝 **Special IP Pool selection**: Optimize for fast, quality, or quantity of IPs
- 🔧 **Easy Integration**: Compatible with most software and programming languages

[![Evomi Banner](https://my.evomi.com/images/brand/cta.png)](https://evomi.com?utm_source=github&utm_medium=banner&utm_campaign=daijro-hrequests)

---

# Installation

Install via pip:

```bash
pip install -U hrequests[all]
python -m hrequests install
```

<details>
<summary>Or, install without headless browsing support</i></summary>

**Ignore the `[all]` option if you don't want headless browsing support:**

```bash
pip install -U hrequests
```

</details>

---

# Documentation

**For the latest stable hrequests documentation, check the [Gitbook page](https://daijro.gitbook.io/hrequests/).**

1. [Simple Usage](#simple-usage)
2. [Sessions](#sessions)
3. [Concurrent & Lazy Requests](#concurrent--lazy-requests)
4. [HTML Parsing](#html-parsing)
5. [Browser Automation](#browser-automation)
6. [Evomi Proxies](#evomi-proxies)

<hr width=50>

## Simple Usage

Here is an example of a simple `get` request:

```py
>>> resp = hrequests.get('https://www.google.com/')
```

Requests are sent through [bogdanfinn's tls-client](https://github.com/bogdanfinn/tls-client) to spoof the TLS client fingerprint. This is done automatically, and is completely transparent to the user.

Other request methods include `post`, `put`, `delete`, `head`, `options`, and `patch`.

The `Response` object is a near 1:1 replica of the `requests.Response` object, with some additional attributes.

<details>
<summary>Parameters</summary>

```
Parameters:
    url (Union[str, Iterable[str]]): URL or list of URLs to request.
    data (Union[str, bytes, bytearray, dict], optional): Data to send to request. Defaults to None.
    files (Dict[str, Union[BufferedReader, tuple]], optional): Data to send to request. Defaults to None.
    headers (dict, optional): Dictionary of HTTP headers to send with the request. Defaults to None.
    params (dict, optional): Dictionary of URL parameters to append to the URL. Defaults to None.
    cookies (Union[RequestsCookieJar, dict, list], optional): Dict or CookieJar to send. Defaults to None.
    json (dict, optional): Json to send in the request body. Defaults to None.
    allow_redirects (bool, optional): Allow request to redirect. Defaults to True.
    history (bool, optional): Remember request history. Defaults to False.
    verify (bool, optional): Verify the server's TLS certificate. Defaults to True.
    timeout (float, optional): Timeout in seconds. Defaults to 30.
    proxy (str, optional): Proxy URL. Defaults to None.
    nohup (bool, optional): Run the request in the background. Defaults to False.
    <Additionally includes all parameters from `hrequests.Session` if a session was not specified>

Returns:
    hrequests.response.Response: Response object
```

</details>

### Properties

Get the response url:

```py
>>> resp.url: str
'https://www.google.com/'
```

Check if the request was successful:

```py
>>> resp.status_code: int
200
>>> resp.reason: str
'OK'
>>> resp.ok: bool
True
>>> bool(resp)
True
```

Getting the response body:

```py
>>> resp.text: str
'<!doctype html><html itemscope="" itemtype="http://schema.org/WebPage" lang="en"><head><meta charset="UTF-8"><meta content="origin" name="referrer"><m...'
>>> resp.content: bytes
b'<!doctype html><html itemscope="" itemtype="http://schema.org/WebPage" lang="en"><head><meta charset="UTF-8"><meta content="origin" name="referrer"><m...'
>>> resp.encoding: str
'UTF-8'
```

Parse the response body as JSON:

```py
>>> resp.json(): Union[dict, list]
{'somedata': True}
```

Get the elapsed time of the request:

```py
>>> resp.elapsed: datetime.timedelta
datetime.timedelta(microseconds=77768)
```

Get the response cookies:

```py
>>> resp.cookies: RequestsCookieJar
<RequestsCookieJar[Cookie(version=0, name='1P_JAR', value='2023-07-05-20', port=None, port_specified=False, domain='.google.com', domain_specified=True...
```

Get the response headers:

```py
>>> resp.headers: CaseInsensitiveDict
{'Alt-Svc': 'h3=":443"; ma=2592000,h3-29=":443"; ma=2592000', 'Cache-Control': 'private, max-age=0', 'Content-Encoding': 'br', 'Content-Length': '51288', 'Content-Security-Policy-Report-Only': "object-src 'none';base-uri 'se
```

<hr width=50>

## Sessions

Creating a new Firefox Session object:

```py
>>> session = hrequests.Session()  # version randomized by default
>>> session = hrequests.Session('firefox', version=129)
```

<details>
<summary>Parameters</summary>

```
Parameters:
    browser (Literal['firefox', 'chrome'], optional): Browser to use. Default is 'chrome'.
    version (int, optional): Version of the browser to use. Browser must be specified. Default is randomized.
    os (Literal['win', 'mac', 'lin'], optional): OS to use in header. Default is randomized.
    headers (dict, optional): Dictionary of HTTP headers to send with the request. Default is generated from `browser` and `os`.
    verify (bool, optional): Verify the server's TLS certificate. Defaults to True.
    timeout (float, optional): Default timeout in seconds. Defaults to 30.
    proxy (str, optional): Proxy URL. Defaults to None.
    cookies (Union[RequestsCookieJar, dict, list], optional): Cookie Jar, or cookie list/dict to send. Defaults to None.
    certificate_pinning (Dict[str, List[str]], optional): Certificate pinning. Defaults to None.
    disable_ipv6 (bool, optional): Disable IPv6. Defaults to False.
    detect_encoding (bool, optional): Detect encoding. Defaults to True.
    ja3_string (str, optional): JA3 string. Defaults to None.
    h2_settings (dict, optional): HTTP/2 settings. Defaults to None.
    additional_decode (str, optional): Decode response body with "gzip" or "br". Defaults to None.
    pseudo_header_order (list, optional): Pseudo header order. Defaults to None.
    priority_frames (list, optional): Priority frames. Defaults to None.
    header_order (list, optional): Header order. Defaults to None.
    force_http1 (bool, optional): Force HTTP/1. Defaults to False.
    catch_panics (bool, optional): Catch panics. Defaults to False.
    debug (bool, optional): Debug mode. Defaults to False.
```

</details>

Browsers can also be created through the `firefox` and `chrome` shortcuts:

```py
>>> session = hrequests.firefox.Session()
>>> session = hrequests.chrome.Session()
```

<details>
<summary>Parameters</summary>

```
Parameters:
    version (int, optional): Version of the browser to use. Browser must be specified. Default is randomized.
    os (Literal['win', 'mac', 'lin'], optional): OS to use in header. Default is randomized.
    headers (dict, optional): Dictionary of HTTP headers to send with the request. Default is generated from `browser` and `os`.
    verify (bool, optional): Verify the server's TLS certificate. Defaults to True.
    timeout (float, optional): Default timeout in seconds. Defaults to 30.
    proxy (str, optional): Proxy URL. Defaults to None.
    cookies (Union[RequestsCookieJar, dict, list], optional): Cookie Jar, or cookie list/dict to send. Defaults to None.
    certificate_pinning (Dict[str, List[str]], optional): Certificate pinning. Defaults to None.
    disable_ipv6 (bool, optional): Disable IPv6. Defaults to False.
    detect_encoding (bool, optional): Detect encoding. Defaults to True.
    ja3_string (str, optional): JA3 string. Defaults to None.
    h2_settings (dict, optional): HTTP/2 settings. Defaults to None.
    additional_decode (str, optional): Decode response body with "gzip" or "br". Defaults to None.
    pseudo_header_order (list, optional): Pseudo header order. Defaults to None.
    priority_frames (list, optional): Priority frames. Defaults to None.
    header_order (list, optional): Header order. Defaults to None.
    force_http1 (bool, optional): Force HTTP/1. Defaults to False.
    catch_panics (bool, optional): Catch panics. Defaults to False.
    debug (bool, optional): Debug mode. Defaults to False.
```

</details>

`os` can be `'win'`, `'mac'`, or `'lin'`. Default is randomized.

```py
>>> session = hrequests.chrome.Session(os='mac')
```

This will automatically generate headers based on the browser name and OS:

```py
>>> session.headers
{'Accept': '*/*', 'Connection': 'keep-alive', 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4; rv:60.2.2) Gecko/20100101 Firefox/60.2.2', 'Accept-Encoding': 'gzip, deflate, br', 'Pragma': 'no-cache'}
```

<details>
<summary>Why is the browser version in the header different than the TLS browser version?</summary>

Website bot detection systems typically do not correlate the TLS fingerprint browser version with the browser header.

By adding more randomization to our headers, we can make our requests appear to be coming from a larger number of clients. We can make it seem like our requests are coming from a larger number of clients. This makes it harder for websites to identify and block our requests based on a consistent browser version.

</details>

### Properties

Here is a simple get request. This is a wrapper around `hrequests.get`. The only difference is that the session cookies are updated with each request. Creating sessions are recommended for making multiple requests to the same domain.

```py
>>> resp = session.get('https://www.google.com/')
```

Session cookies update with each request:

```py
>>> session.cookies: RequestsCookieJar
<RequestsCookieJar[Cookie(version=0, name='1P_JAR', value='2023-07-05-20', port=None, port_specified=False, domain='.google.com', domain_specified=True...
```

Regenerate headers for a different OS:

```py
>>> session.os = 'win'
>>> session.headers: CaseInsensitiveDict
{'Accept': '*/*', 'Connection': 'keep-alive', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0.3) Gecko/20100101 Firefox/66.0.3', 'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-US;q=0.5,en;q=0.3', 'Cache-Control': 'max-age=0', 'DNT': '1', 'Upgrade-Insecure-Requests': '1', 'Pragma': 'no-cache'}
```

### Closing Sessions

Sessions can also be closed to free memory:

```py
>>> session.close()
```

Alternatively, sessions can be used as context managers:

```py
with hrequests.Session() as session:
    resp = session.get('https://www.google.com/')
    print(resp)
```

<hr width=50>

## Concurrent & Lazy Requests

### Nohup Requests

Similar to Unix's nohup command, `nohup` requests are sent in the background.

Adding the `nohup=True` keyword argument will return a `LazyTLSRequest` object. This will send the request immediately, but doesn't wait for the response to be ready until an attribute of the response is accessed.

```py
resp1 = hrequests.get('https://www.google.com/', nohup=True)
resp2 = hrequests.get('https://www.google.com/', nohup=True)
```

`resp1` and `resp2` are sent concurrently. They will _never_ pause the current thread, unless an attribute of the response is accessed:

```py
print('Resp 1:', resp1.reason)  # will wait for resp1 to finish, if it hasn't already
print('Resp 2:', resp2.reason)  # will wait for resp2 to finish, if it hasn't already
```

This is useful for sending requests in the background that aren't needed until later.

Note: In `nohup`, a new thread is created for each request. For larger scale concurrency, please consider the following:

### Easy Concurrency

You can pass an array/iterator of links to the request methods to send them concurrently. This wraps around [`hrequests.map`](#map):

```py
>>> hrequests.get(['https://google.com/', 'https://github.com/'])
(<Response [200]>, <Response [200]>)
```

This also works with `nohup`:

```py
>>> resps = hrequests.get(['https://google.com/', 'https://github.com/'], nohup=True)
>>> resps
(<LazyResponse[Pending]>, <LazyResponse[Pending]>)
>>> # Sometime later...
>>> resps
(<Response [200]>, <Response [200]>)
```

### Grequests-style Concurrency

The methods `async_get`, `async_post`, etc. will create an unsent request. This levereges gevent, making it _blazing fast_.

<details>
<summary>Parameters</summary>

```
Parameters:
    url (str): URL to send request to
    data (Union[str, bytes, bytearray, dict], optional): Data to send to request. Defaults to None.
    files (Dict[str, Union[BufferedReader, tuple]], optional): Data to send to request. Defaults to None.
    headers (dict, optional): Dictionary of HTTP headers to send with the request. Defaults to None.
    params (dict, optional): Dictionary of URL parameters to append to the URL. Defaults to None.
    cookies (Union[RequestsCookieJar, dict, list], optional): Dict or CookieJar to send. Defaults to None.
    json (dict, optional): Json to send in the request body. Defaults to None.
    allow_redirects (bool, optional): Allow request to redirect. Defaults to True.
    history (bool, optional): Remember request history. Defaults to False.
    verify (bool, optional): Verify the server's TLS certificate. Defaults to True.
    timeout (float, optional): Timeout in seconds. Defaults to 30.
    proxy (str, optional): Proxy URL. Defaults to None.
    <Additionally includes all parameters from `hrequests.Session` if a session was not specified>

Returns:
    hrequests.response.Response: Response object
```

</details>

Async requests are evaluated on `hrequests.map`, `hrequests.imap`, or `hrequests.imap_enum`.

This functionality is similar to [grequests](https://github.com/spyoungtech/grequests). Unlike grequests, [monkey patching](https://www.gevent.org/api/gevent.monkey.html) is not required because this does not rely on the standard python SSL library.

Create a set of unsent Requests:

```py
>>> reqs = [
...     hrequests.async_get('https://www.google.com/', browser='firefox'),
...     hrequests.async_get('https://www.duckduckgo.com/'),
...     hrequests.async_get('https://www.yahoo.com/')
... ]
```

#### map

Send them all at the same time using map:

```py
>>> hrequests.map(reqs, size=3)
[<Response [200]>, <Response [200]>, <Response [200]>]
```

<details>
<summary>Parameters</summary>

```
Concurrently converts a list of Requests to Responses.
Parameters:
    requests - a collection of Request objects.
    size - Specifies the number of requests to make at a time. If None, no throttling occurs.
    exception_handler - Callback function, called when exception occurred. Params: Request, Exception
    timeout - Gevent joinall timeout in seconds. (Note: unrelated to requests timeout)

Returns:
    A list of Response objects.
```

</details>

#### imap

`imap` returns a generator that yields responses as they come in:

```py
>>> for resp in hrequests.imap(reqs, size=3):
...    print(resp)
<Response [200]>
<Response [200]>
<Response [200]>
```

<details>
<summary>Parameters</summary>

```
Concurrently converts a generator object of Requests to a generator of Responses.

Parameters:
    requests - a generator or sequence of Request objects.
    size - Specifies the number of requests to make at a time. default is 2
    exception_handler - Callback function, called when exception occurred. Params: Request, Exception

Yields:
    Response objects.
```

</details>

`imap_enum` returns a generator that yields a tuple of `(index, response)` as they come in. The `index` is the index of the request in the original list:

```py
>>> for index, resp in hrequests.imap_enum(reqs, size=3):
...     print(index, resp)
(1, <Response [200]>)
(0, <Response [200]>)
(2, <Response [200]>)
```

<details>
<summary>Parameters</summary>

```
Like imap, but yields tuple of original request index and response object
Unlike imap, failed results and responses from exception handlers that return None are not ignored. Instead, a
tuple of (index, None) is yielded.
Responses are still in arbitrary order.

Parameters:
    requests - a sequence of Request objects.
    size - Specifies the number of requests to make at a time. default is 2
    exception_handler - Callback function, called when exception occurred. Params: Request, Exception

Yields:
    (index, Response) tuples.
```

</details>

#### Exception Handling

To handle timeouts or any other exception during the connection of the request, you can add an optional exception handler that will be called with the request and exception inside the main thread.

```py
>>> def exception_handler(request, exception):
...    return f'Response failed: {exception}'

>>> bad_reqs = [
...     hrequests.async_get('http://httpbin.org/delay/5', timeout=1),
...     hrequests.async_get('http://fakedomain/'),
...     hrequests.async_get('http://example.com/'),
... ]
>>> hrequests.map(bad_reqs, size=3, exception_handler=exception_handler)
['Response failed: Connection error', 'Response failed: Connection error', <Response [200]>]
```

The value returned by the exception handler will be used in place of the response in the result list.

If an exception handler isn't specified, the default yield type is `hrequests.FailedResponse`.

<hr width=50>

## HTML Parsing

HTML scraping is based off [selectolax](https://github.com/rushter/selectolax), which is **over 25x faster** than bs4. This functionality is inspired by [requests-html](https://github.com/psf/requests-html).

| Library        | Time (1e5 trials) |
| -------------- | ----------------- |
| BeautifulSoup4 | 52.6              |
| PyQuery        | 7.5               |
| selectolax     | **1.9**           |

The HTML parser can be accessed through the `html` attribute of the response object:

```py
>>> resp = session.get('https://python.org/')
>>> resp.html
<HTML url='https://www.python.org/'>
```

### Parsing page

Grab a list of all links on the page, as-is (anchors excluded):

```py
>>> resp.html.links
{'//docs.python.org/3/tutorial/', '/about/apps/', 'https://github.com/python/pythondotorg/issues', '/accounts/login/', '/dev/peps/', '/about/legal/',...
```

Grab a list of all links on the page, in absolute form (anchors excluded):

```py
>>> resp.html.absolute_links
{'https://github.com/python/pythondotorg/issues', 'https://docs.python.org/3/tutorial/', 'https://www.python.org/about/success/', 'http://feedproxy.g...
```

Search for text on the page:

```py
>>> resp.html.search('Python is a {} language')[0]
programming
```

### Selecting elements

Select an element using a CSS Selector:

```py
>>> about = resp.html.find('#about')
```

<details>
<summary>Parameters</summary>

```
Given a CSS Selector, returns a list of
:class:`Element <Element>` objects or a single one.

Parameters:
    selector: CSS Selector to use.
    clean: Whether or not to sanitize the found HTML of ``<script>`` and ``<style>``
    containing: If specified, only return elements that contain the provided text.
    first: Whether or not to return just the first result.
    raise_exception: Raise an exception if no elements are found. Default is True.
    _encoding: The encoding format.

Returns:
    A list of :class:`Element <Element>` objects or a single one.

Example CSS Selectors:
- ``a``
- ``a.someClass``
- ``a#someID``
- ``a[target=_blank]``
See W3School's `CSS Selectors Reference
<https://www.w3schools.com/cssref/css_selectors.asp>`_
for more details.
If ``first`` is ``True``, only returns the first
:class:`Element <Element>` found.
```

</details>

### Introspecting elements

Grab an Element's text contents:

```py
>>> print(about.text)
About
Applications
Quotes
Getting Started
Help
Python Brochure
```

Getting an Element's attributes:

```py
>>> about.attrs
{'id': 'about', 'class': ('tier-1', 'element-1'), 'aria-haspopup': 'true'}
>>> about.id
'about'
```

Get an Element's raw HTML:

```py
>>> about.html
'<li aria-haspopup="true" class="tier-1 element-1 " id="about">\n<a class="" href="/about/" title="">About</a>\n<ul aria-hidden="true" class="subnav menu" role="menu">\n<li class="tier-2 element-1" role="treeitem"><a href="/about/apps/" title="">Applications</a></li>\n<li class="tier-2 element-2" role="treeitem"><a href="/about/quotes/" title="">Quotes</a></li>\n<li class="tier-2 element-3" role="treeitem"><a href="/about/gettingstarted/" title="">Getting Started</a></li>\n<li class="tier-2 element-4" role="treeitem"><a href="/about/help/" title="">Help</a></li>\n<li class="tier-2 element-5" role="treeitem"><a href="http://brochure.getpython.info/" title="">Python Brochure</a></li>\n</ul>\n</li>'
```

Select Elements within Elements:

```py
>>> about.find_all('a')
[<Element 'a' href='/about/' title='' class=''>, <Element 'a' href='/about/apps/' title=''>, <Element 'a' href='/about/quotes/' title=''>, <Element 'a' href='/about/gettingstarted/' title=''>, <Element 'a' href='/about/help/' title=''>, <Element 'a' href='http://brochure.getpython.info/' title=''>]
>>> about.find('a')
<Element 'a' href='/about/' title='' class=''>
```

Searching by HTML attributes:

```py
>>> about.find('il', role='treeitem')
<Element 'li' role='treeitem' class=('tier-2', 'element-1')>
```

Search for links within an element:

```py
>>> about.absolute_links
{'http://brochure.getpython.info/', 'https://www.python.org/about/gettingstarted/', 'https://www.python.org/about/', 'https://www.python.org/about/quotes/', 'https://www.python.org/about/help/', 'https://www.python.org/about/apps/'}
```

<hr width=50>

## Browser Automation

Hrequests supports both Firefox and Chrome browsers, headless and headful sessions:

> [!WARNING]
> It is recommended to use Firefox instead. Chrome does not support fingerprint rotation, mocking human mouse movements, or browser extensions.

### Usage

You can spawn a `BrowserSession` instance by calling it:

```py
>>> page = hrequests.BrowserSession()  # headless=True by default
```

<details>
<summary>Parameters</summary>

```
Parameters:
    session (hrequests.session.TLSSession, optional): Session to use for headers, cookies, etc.
    resp (hrequests.response.Response, optional): Response to update with cookies, headers, etc.
    proxy (Union[str, BaseProxy], optional): Proxy to use for the browser. Example: http://1.2.3.4:8080
    mock_human (bool, optional): Whether to emulate human behavior. Defaults to False.
    engine (BrowserEngine, optional): Pass in an existing BrowserEngine instead of creating a new one
    verify (bool, optional): Whether to verify https requests
    headless (bool, optional): Whether to run the browser in headless mode. Defaults to True.
    os (Literal['win', 'mac', 'lin'], optional): Generate headers for a specific OS
    **kwargs: Additional arguments to pass to Playwright (or Camoufox parameters if using Firefox)
```

</details>

`BrowserSession` is entirely safe to use across threads.

#### Camoufox Integration

If you are using a Firefox BrowserSession, you can pass additional parameters to Camoufox by using the `**kwargs` parameter:

```py
>>> page = hrequests.BrowserSession(window=(1024, 768), block_images=True, addons=['/path/to/addon'], ...)
```

You can find a full list of parameters for Camoufox [here](https://camoufox.com/python/usage).

#### Engine

The `engine` parameter allows you to pass in an existing `BrowserEngine` instance. This can be useful if you want to reuse a Playwright engine to save time on startup. It is completely threadsafe.

```python
>>> engine = hrequests.BrowserEngine()
```

Use the same engine for multiple sessions

```python
>>> page1 = hrequests.BrowserSession(engine=engine)
>>> page2 = hrequests.BrowserSession(engine=engine)
```

### Render an existing Response

Responses have a `.render()` method. This will render the contents of the response in a browser page.

Once the page is closed, the Response content and the Response's session cookies will be updated.

#### Simple usage

Rendered browser sessions will use the browser set in the initial request.

You can set a request's browser with the `browser` parameter in the `hrequests.get` method:

```py
>>> resp = hrequests.get('https://example.com')
```

Or by setting the `browser` parameter of the `hrequests.Session` object:

```py
>>> session = hrequests.Session()
>>> resp = session.get('https://example.com')
```

**Example - submitting a login form:**

```py
>>> session = hrequests.Session()
>>> resp = session.get('https://www.somewebsite.com/')
>>> with resp.render(mock_human=True) as page:
...     page.type('.input#username', 'myuser')
...     page.type('.input#password', 'p4ssw0rd')
...     page.click('#submit')
# `session` & `resp` now have updated cookies, content, etc.
```

<summary><strong>Or, without a context manager</strong></summary>

```py
>>> session = hrequests.Session()
>>> resp = session.get('https://www.somewebsite.com/')
>>> page = resp.render(mock_human=True)
>>> page.type('.input#username', 'myuser')
>>> page.type('.input#password', 'p4ssw0rd')
>>> page.click('#submit')
>>> page.close()  # must close the page when done!
```

</details>

The `mock_human` parameter will emulate human-like behavior. This includes easing and randomizing mouse movements, and randomizing typing speed. This functionality is based on [Botright](https://github.com/Vinyzu/botright/).

<details>
<summary>Parameters</summary>

```
Parameters:
    headless (bool, optional): Whether to run the browser in headless mode. Defaults to False.
    mock_human (bool, optional): Whether to emulate human behavior. Defaults to False.
    extensions (Union[str, Iterable[str]], optional): Path to a folder of unpacked extensions, or a list of paths to unpacked extensions
    engine (BrowserEngine, optional): Pass in an existing BrowserEngine instead of creating a new one
    **kwargs: Additional arguments to pass to Camoufox (see https://camoufox.com/python/usage)
```

</details>

### Properties

Cookies are inherited from the session:

```py
>>> page.cookies: RequestsCookieJar  # cookies are inherited from the session
<RequestsCookieJar[Cookie(version=0, name='1P_JAR', value='2023-07-05-20', port=None, port_specified=False, domain='.somewebsite.com', domain_specified=True...
```

### Pulling page data

Get current page url:

```py
>>> page.url: str
https://www.somewebsite.com/
```

Get page content:

```py
>>> page.text: str
'<!doctype html><html itemscope="" itemtype="http://schema.org/WebPage" lang="en"><head><meta content="Search the world\'s information, including webpag'
>>> page.content: bytes
b'<!doctype html><html itemscope="" itemtype="http://schema.org/WebPage" lang="en"><head><meta content="Search the world\'s information, including webpag'
```

Get the status of the last navigation:

```py
>>> page.status_code: int
200
>>> page.reason: str
'OK'
```

Parsing HTML from the page content:

```py
>>> page.html.find_all('a')
[<Element 'a' href='/about/' title='' class=''>, <Element 'a' href='/about/apps/' title=''>, ...]
>>> page.html.find('a')
<Element 'a' href='/about/' title='' class=''>, <Element 'a' href='/about/apps/' title=''>
```

Take a screenshot of the page:

```py
>>> page.screenshot(path='screenshot.png')
```

<details>
<summary>Parameters</summary>

```
Take a screenshot of the page

Parameters:
    selector (str, optional): CSS selector to screenshot
    path (str, optional): Path to save screenshot to. Defaults to None.
    full_page (bool): Whether to take a screenshot of the full scrollable page. Cannot be used with selector. Defaults to False.

Returns:
    Optional[bytes]: Returns the screenshot buffer, if `path` was not provided
```

</details>

### Navigate the browser

Navigate to a url:

```py
>>> page.url = 'https://bing.com'
# or use goto
>>> page.goto('https://bing.com')
```

Navigate through page history:

```py
>>> page.back()
>>> page.forward()
```

### Controlling elements

Click an element:

```py
>>> page.click('#my-button')
# or through the html parser
>>> page.html.find('#my-button').click()
```

<details>
<summary>Parameters</summary>

```
Parameters:
    selector (str): CSS selector to click.
    button (Literal['left', 'right', 'middle'], optional): Mouse button to click. Defaults to 'left'.
    count (int, optional): Number of clicks. Defaults to 1.
    timeout (float, optional): Timeout in seconds. Defaults to 30.
    wait_after (bool, optional): Wait for a page event before continuing. Defaults to True.
```

</details>

Hover over an element:

```py
>>> page.hover('.dropbtn')
# or through the html parser
>>> page.html.find('.dropbtn').hover()
```

<details>
<summary>Parameters</summary>

```
Parameters:
    selector (str): CSS selector to hover over
    modifiers (List[Literal['Alt', 'Control', 'Meta', 'Shift']], optional): Modifier keys to press. Defaults to None.
    timeout (float, optional): Timeout in seconds. Defaults to 90.
```

</details>

Type text into an element:

```py
>>> page.type('#my-input', 'Hello world!')
# or through the html parser
>>> page.html.find('#my-input').type('Hello world!')
```

<details>
<summary>Parameters</summary>

```
Parameters:
    selector (str): CSS selector to type in
    text (str): Text to type
    delay (int, optional): Delay between keypresses in ms. On mock_human, this is randomized by 50%. Defaults to 50.
    timeout (float, optional): Timeout in seconds. Defaults to 30.
```

</details>

Drag and drop an element:

```py
>>> page.dragTo('#source-selector', '#target-selector')
# or through the html parser
>>> page.html.find('#source-selector').dragTo('#target-selector')
```

<details>
<summary>Parameters</summary>

```
Parameters:
    source (str): Source to drag from
    target (str): Target to drop to
    timeout (float, optional): Timeout in seconds. Defaults to 30.
    wait_after (bool, optional): Wait for a page event before continuing. Defaults to False.
    check (bool, optional): Check if an element is draggable before running. Defaults to False.

Throws:
    hrequests.exceptions.BrowserTimeoutException: If timeout is reached
```

</details>

### Check page elements

Check if a selector is visible and enabled:

```py
>>> page.isVisible('#my-selector'): bool
>>> page.isEnabled('#my-selector'): bool
```

<details>
<summary>Parameters</summary>

```
Parameters:
    selector (str): Selector to check
```

</details>

Evaluate and return a script:

```py
>>> page.evaluate('selector => document.querySelector(selector).checked', '#my-selector')
```

<details>
<summary>Parameters</summary>

```
Parameters:
    script (str): Javascript to evaluate in the page
    arg (str, optional): Argument to pass into the javascript function
```

</details>

### Awaiting events

```py
>>> page.awaitNavigation()
```

<details>
<summary>Parameters</summary>

```
Parameters:
    timeout (float, optional): Timeout in seconds. Defaults to 30.

Throws:
    hrequests.exceptions.BrowserTimeoutException: If timeout is reached
```

</details>

Wait for a script or function to return a truthy value:

```py
>>> page.awaitScript('selector => document.querySelector(selector).value === 100', '#progress')
```

<details>
<summary>Parameters</summary>

```
Parameters:
    script (str): Script to evaluate
    arg (str, optional): Argument to pass to script
    timeout (float, optional): Timeout in seconds. Defaults to 30.

Throws:
    hrequests.exceptions.BrowserTimeoutException: If timeout is reached
```

</details>

Wait for the URL to match:

```py
>>> page.awaitUrl(re.compile(r'https?://www\.google\.com/.*'), timeout=10)
```

<details>
<summary>Parameters</summary>

```
Parameters:
    url (Union[str, Pattern[str], Callable[[str], bool]]) - URL to match for
    timeout (float, optional): Timeout in seconds. Defaults to 30.

Throws:
    hrequests.exceptions.BrowserTimeoutException: If timeout is reached
```

</details>

Wait for an element to exist on the page:

```py
>>> page.awaitSelector('#my-selector')
# or through the html parser
>>> page.html.find('#my-selector').awaitSelector()
```

<details>
<summary>Parameters</summary>

```
Parameters:
    selector (str): Selector to wait for
    timeout (float, optional): Timeout in seconds. Defaults to 30.

Throws:
    hrequests.exceptions.BrowserTimeoutException: If timeout is reached
```

</details>

Wait for an element to be enabled:

```py
>>> page.awaitEnabled('#my-selector')
# or through the html parser
>>> page.html.find('#my-selector').awaitEnabled()
```

<details>
<summary>Parameters</summary>

```
Parameters:
    selector (str): Selector to wait for
    timeout (float, optional): Timeout in seconds. Defaults to 30.

Throws:
    hrequests.exceptions.BrowserTimeoutException: If timeout is reached
```

</details>

Screenshot an element:

```py
>>> page.screenshot('#my-selector', path='screenshot.png')
# or through the html parser
>>> page.html.find('#my-selector').screenshot('selector.png')
```

<details>
<summary>Parameters</summary>

```
Screenshot an element

Parameters:
    selector (str, optional): CSS selector to screenshot
    path (str, optional): Path to save screenshot to. Defaults to None.
    full_page (bool): Whether to take a screenshot of the full scrollable page. Cannot be used with selector. Defaults to False.

Returns:
    Optional[bytes]: Returns the screenshot buffer, if `path` was not provided
```

</details>

### Adding Firefox extensions

Firefox extensions can be easily imported into a browser session. Some potentially useful extensions include:

- **uBlock Origin** - Ad & popup blocker (Automatically installed)

- **hektCaptcha** - Hcaptcha solver ([Download](https://github.com/Wikidepia/hektCaptcha-extension))

- **FastForward** - Bypass & skip link redirects ([Download](https://nightly.link/FastForwardTeam/FastForward/workflows/main/main/FastForward_firefox.zip))

**Note:** Hrequests only supports Firefox extensions.

Extensions are added with the `extensions` parameter:

- This can be an list of absolute paths to unpacked extensions:

  ```py
  with resp.render(extensions=['C:\\extensions\\hektcaptcha', 'C:\\extensions\\fastforward']):
  ```

Here is an usage example of using a captcha solver:

```py
>>> resp = hrequests.get('https://accounts.hcaptcha.com/demo', browser='firefox')
>>> with resp.render(extensions=['C:\\extensions\\hektcaptcha']) as page:
...     page.awaitSelector('.hcaptcha-success')  # wait for captcha to finish
...     page.click('input[type=submit]')
```

### Requests & Responses

Requests can also be sent within browser sessions. These operate the same as the standard `hrequests.request`, and will use the browser's cookies and headers. The `BrowserSession` cookies will be updated with each request.

This returns a normal `Response` object:

```py
>>> resp = page.get('https://duckduckgo.com')
```

<details>
<summary>Parameters</summary>

```
Parameters:
    url (str): URL to send request to
    params (dict, optional): Dictionary of URL parameters to append to the URL. Defaults to None.
    data (Union[str, dict], optional): Data to send to request. Defaults to None.
    headers (dict, optional): Dictionary of HTTP headers to send with the request. Defaults to None.
    form (dict, optional): Form data to send with the request. Defaults to None.
    multipart (dict, optional): Multipart data to send with the request. Defaults to None.
    timeout (float, optional): Timeout in seconds. Defaults to 30.
    verify (bool, optional): Verify the server's TLS certificate. Defaults to True.
    max_redirects (int, optional): Maximum number of redirects to follow. Defaults to None.

Throws:
    hrequests.exceptions.BrowserTimeoutException: If timeout is reached

Returns:
    hrequests.response.Response: Response object
```

</details>

Other methods include `post`, `put`, `delete`, `head`, and `patch`.

### Closing the page

The `BrowserSession` object must be closed when finished. This will close the browser, update the response data, and merge new cookies with the session cookies.

```py
>>> page.close()
```

Note that this is automatically done when using a context manager.

Session cookies are updated:

```py
>>> session.cookies: RequestsCookieJar
<RequestsCookieJar[Cookie(version=0, name='MUID', value='123456789', port=None, port_specified=False, domain='.bing.com', domain_specified=True, domain_initial_dot=True...
```

Response data is updated:

```py
>>> resp.url: str
'https://www.bing.com/?toWww=1&redig=823778234657823652376438'
>>> resp.content: Union[bytes, str]
'<!DOCTYPE html><html lang="en" dir="ltr"><head><meta name="theme-color" content="#4F4F4F"><meta name="description" content="Bing helps you turn inform...
```

#### Other ways to create a Browser Session

You can use `.render` to spawn a `BrowserSession` object directly from a url:

```py
# Using a Session:
>>> page = session.render('https://google.com')
# Or without a session at all:
>>> page = hrequests.render('https://google.com')
```

Make sure to close all `BrowserSession` objects when done!

```py
>>> page.close()
```

<hr width=50>

## Evomi Proxies

Hrequests has a built in residential proxy rotation service powered by [Evomi](https://evomi.com/).

### Creating a proxy

Import the `evomi` module:

```py
>>> from hrequests.proxies import evomi
>>> proxy = evomi.ResidentialProxy(username='daijro', key='password')
```

### Usage

Pass proxies into requests:

```
>>> resp = hrequests.get('https://example.com', proxy=proxy)
```

Use Evomi proxies with a `Session`:

```python
# Add the proxy to the session
>>> session = hrequests.Session(proxy=proxy)
# All requests made with this session will use the proxy.
>>> resp = session.get('https://example.com')
>>> with resp.render() as page:
...     # Page is rendered with the proxy.
...     ...
```

Use Evomi proxies with a `BrowserSession`:

```python
>>> page = hrequests.BrowserSession(proxy=proxy)
>>> page.goto('https://example.com')
```

### Proxy Types

You can create either a residential, mobile, or datacenter proxy:

#### Residential

```py
>>> proxy = evomi.ResidentialProxy(username='daijro', key='password')
```

<details>
<summary>ResidentialProxy Parameters</summary>

```
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
```

</details>

#### Mobile

```py
>>> proxy = evomi.MobileProxy(username='daijro', key='password')
```

<details>
<summary>MobileProxy Parameters</summary>

```
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
```

</details>

#### Datacenter

```py
>>> proxy = evomi.DatacenterProxy(username='daijro', key='password')
```

<details>
<summary>DatacenterProxy Parameters</summary>

```
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
```

</details>

### Parameter Table

| Parameter      | Description                                           | Residential | Mobile | Datacenter |
| -------------- | ----------------------------------------------------- | ----------- | ------ | ---------- |
| `continent`    | Continent name                                        | ✔️          | ✔️     | ✔️         |
| `country`      | Country code                                          | ✔️          | ✔️     | ✔️         |
| `region`       | Region, state, province, or territory                 | ✔️          | ✔️     |
| `city`         | City name                                             | ✔️          |        |
| `isp`          | ISP name                                              | ✔️          | ✔️     |
| `pool`         | Proxy pool. Takes standard, speed, or quality.        | ✔️          |        |
| `session_type` | Session persistence type                              | ✔️          | ✔️     | ✔️         |
| `auto_rotate`  | Whether to automatically rotate IPs between requests. | ✔️          | ✔️     | ✔️         |
| `lifetime`     | Duration of the session in minutes (1-120)            | ✔️          | ✔️     | ✔️         |
| `adblock`      | Whether to enable ad blocking                         | ✔️          |        |

### Geo-targetting

Specify the geographic location of the proxy:

#### Continent

Possible options are `Africa`, `Asia`, `Europe`, `Oceania`, `North America`, and `South America`.

```py
>>> proxy = evomi.ResidentialProxy(continent='North America', ...)
```

#### Country

Target a specific country. Takes two-letter country codes.

```py
>>> proxy = evomi.ResidentialProxy(country='US', ...)  # United States
>>> proxy = evomi.ResidentialProxy(country='CA', ...)  # Canada
```

#### City

Target a specific city. Residential proxies only.

```py
>>> proxy = evomi.ResidentialProxy(city='New York', ...)
>>> proxy = evomi.ResidentialProxy(city='Tokyo', ...)
```

#### Region

Target a specific state, province, or territory. Residential and Mobile proxies only.

```py
>>> proxy = evomi.ResidentialProxy(region='California', ...)
>>> proxy = evomi.ResidentialProxy(region='Southern Cape', ...)
```

---

## Thanks

This project includes code adapted from the following sources:

- **tls-client**

  - Author: bogdanfinn
  - Repository: https://github.com/bogdanfinn/tls-client
  - License: BSD-4-Clause license
  - Used in [bridge/server.go](https://github.com/daijro/hrequests/blob/main/bridge/server.go)

- **Minet**

  - Author: medialab
  - Repository: https://github.com/medialab/minet
  - License: GPL-3.0
  - Inspired the threadsafe implementation of Playwright

- **Patchright**
  - Author: Vinyzu and Kaliiiiiiiiii
  - Repository: https://github.com/Kaliiiiiiiiii-Vinyzu/patchright
  - License: Apache License 2.0
  - Used for Chrome browser support
