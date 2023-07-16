import contextlib
import re
import weakref
from functools import partial
from typing import List, MutableMapping, Optional, Set, Union
from urllib.parse import urljoin, urlparse, urlunparse

import lxml
from lxml import etree
from lxml.html import HtmlElement
from lxml.html import tostring as lxml_html_tostring
from lxml.html.clean import Cleaner
from lxml.html.soupparser import fromstring as soup_parse
from parse import Result, findall
from parse import search as parse_search
from pyquery import PyQuery
from w3lib.encoding import html_to_unicode

import hrequests
from hrequests.exceptions import NotRenderedException

"""
Based off https://github.com/psf/requests-html/blob/master/requests_html.py
Copyright 2018 Kenneth Reitz

Used as an alternative to beautifulsoup4:
==== Total trials: 100000 =====
bs4 total time: 52.6
pq total time: 7.5
"""


DEFAULT_ENCODING = 'utf-8'
DEFAULT_URL = 'https://example.org/'
DEFAULT_NEXT_SYMBOL = ['next', 'more', 'older']


# Typing
_Find = Union[List['Element'], 'Element']
_XPath = Union[List[str], List['Element'], str, 'Element']
_Result = Union[List['Result'], 'Result']
_HTML = Union[str, bytes]
_Containing = Union[str, List[str]]
_Links = Set[str]
_Next = Union['HTML', List[str]]
_NextSymbol = List[str]


class BaseParser:
    """
    A basic HTML/Element Parser, for Humans.

    Args:
        element: The element from which to base the parsing upon.
        default_encoding: Which encoding to default to.
        html: HTML from which to base the parsing upon (optional).
        url: The URL from which the HTML originated, used for ``absolute_links``.
    """

    def __init__(
        self,
        *,
        element,
        default_encoding: str = None,
        html: _HTML = None,
        url: str,
        br_session: Optional[weakref.CallableProxyType] = None,
    ) -> None:
        self.element = element
        self.url = url
        self.skip_anchors = True
        self.default_encoding = default_encoding
        self._encoding = None
        self._html = html.encode(DEFAULT_ENCODING) if isinstance(html, str) else html
        self._lxml = None
        self._pq = None
        self.br_session = br_session

        self.cleaner = Cleaner()
        self.cleaner.javascript = True
        self.cleaner.style = True

    # BrowserSession methods that accept a `selector` parameter
    pass_to_session = {
        'awaitSelector',
        'awaitEnabled',
        'isVisible',
        'isEnabled',
        'dragTo',
        'type',
        'click',
        'hover',
    }

    def __getattr__(self, name):
        if name not in self.pass_to_session:
            return
        # pass through to session if it exists
        if self.br_session is None:
            raise NotRenderedException(f'Method {name} only allowed in BrowserSession')
        return partial(getattr(self.br_session, name), self.css_path)

    @property
    def css_path(self) -> str:
        # returns css selector of the element
        xpath = self.element.getroottree().getelementpath(self.element)
        return re.sub(r'\[(\d+)\]', r':nth-of-type(\1)', ' > '.join(xpath.strip('/').split('/')))

    @property
    def raw_html(self) -> bytes:
        """
        Bytes representation of the HTML content.
        (`learn more <http://www.diveintopython3.net/strings.html>`_).
        """
        if self._html:
            return self._html
        else:
            return etree.tostring(self.element, encoding='unicode').strip().encode(self.encoding)

    @property
    def html(self) -> str:
        """
        Unicode representation of the HTML content
        (`learn more <http://www.diveintopython3.net/strings.html>`_).
        """
        if self._html:
            return self.raw_html.decode(self.encoding, errors='replace')
        else:
            return etree.tostring(self.element, encoding='unicode').strip()

    @html.setter
    def html(self, html: str) -> None:
        self._html = html.encode(self.encoding)

    @raw_html.setter
    def raw_html(self, html: bytes) -> None:
        """Property setter for self.html."""
        self._html = html

    @property
    def encoding(self) -> str:
        """
        The encoding string to be used, extracted from the HTML and
        :class:`HTMLResponse <HTMLResponse>` headers.
        """
        if self._encoding:
            return self._encoding

        # Scan meta tags for charset.
        if self._html:
            self._encoding = html_to_unicode(self.default_encoding, self._html)[0]
            # Fall back to requests' detected encoding if decode fails.
            try:
                self.raw_html.decode(self.encoding, errors='replace')
            except UnicodeDecodeError:
                self._encoding = self.default_encoding

        return self._encoding or self.default_encoding

    @encoding.setter
    def encoding(self, enc: str) -> None:
        """Property setter for self.encoding."""
        self._encoding = enc

    @property
    def pq(self) -> PyQuery:
        """
        `PyQuery <https://pythonhosted.org/pyquery/>`_ representation
        of the :class:`Element <Element>` or :class:`HTML <HTML>`.
        """
        if self._pq is None:
            self._pq = PyQuery(self.lxml)

        return self._pq

    @property
    def lxml(self) -> HtmlElement:
        """
        `lxml <http://lxml.de>`_ representation of the
        :class:`Element <Element>` or :class:`HTML <HTML>`.
        """
        if self._lxml is None:
            try:
                self._lxml = soup_parse(self.html, features='html.parser')
            except ValueError:
                self._lxml = lxml.html.fromstring(self.raw_html)

        return self._lxml

    @property
    def text(self) -> str:
        """
        The text content of the
        :class:`Element <Element>` or :class:`HTML <HTML>`.
        """
        return self.pq.text()

    @property
    def full_text(self) -> str:
        """
        The full text content (including links) of the
        :class:`Element <Element>` or :class:`HTML <HTML>`.
        """
        return self.lxml.text_content()

    def find_all(
        self,
        selector: str = "*",
        *,
        containing: _Containing = None,
        clean: bool = False,
        first: bool = False,
        _encoding: str = None,
    ) -> _Find:
        """
        Given a CSS Selector, returns a list of
        :class:`Element <Element>` objects or a single one.

        Args:
            selector: CSS Selector to use.
            clean: Whether or not to sanitize the found HTML of ``<script>`` and ``<style>`` tags.
            containing: If specified, only return elements that contain the provided text.
            first: Whether or not to return just the first result.
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
        """

        # Convert a single containing into a list.
        if isinstance(containing, str):
            containing = [containing]

        encoding = _encoding or self.encoding
        elements = [
            Element(
                element=found, url=self.url, default_encoding=encoding, br_session=self.br_session
            )
            for found in self.pq(selector)
        ]

        if containing:
            elements_copy = elements.copy()
            elements = [
                element
                for element in elements_copy
                if any(c.lower() in element.full_text.lower() for c in containing)
            ]
            elements.reverse()

        # Sanitize the found HTML.
        if clean:
            elements_copy = elements.copy()
            elements = []

            for element in elements_copy:
                element.raw_html = lxml_html_tostring(self.cleaner.clean_html(element.lxml))
                elements.append(element)

        return _get_first_or_list(elements, first)

    def find(
        self,
        selector: str = "*",
        *,
        containing: _Containing = None,
        clean: bool = False,
        _encoding: str = None,
    ) -> _Find:
        # Wrapper around find_all with first=True.
        return self.find_all(
            selector=selector, containing=containing, clean=clean, first=True, _encoding=_encoding
        )

    def xpath(
        self, selector: str, *, clean: bool = False, first: bool = False, _encoding: str = None
    ) -> _XPath:
        """
        Given an XPath selector, returns a list of Element objects or a single one.

        Args:
            selector (str): XPath Selector to use.
            clean (bool, optional): Whether or not to sanitize the found HTML of <script> and <style> tags. Defaults to False.
            first (bool, optional): Whether or not to return just the first result. Defaults to False.
            _encoding (str, optional): The encoding format. Defaults to None.

        Returns:
            _XPath: A list of Element objects or a single one.

        If a sub-selector is specified (e.g. //a/@href), a simple list of results is returned.
        See W3School's XPath Examples for more details.

        If first is True, only returns the first Element found.
        """
        selected = self.lxml.xpath(selector)

        elements = [
            str(selection)
            if isinstance(selection, etree._ElementUnicodeResult)
            else Element(
                element=selection,
                url=self.url,
                default_encoding=_encoding or self.encoding,
                br_session=self.br_session,
            )
            for selection in selected
        ]

        # Sanitize the found HTML.
        if clean:
            elements_copy = elements.copy()
            elements = []

            for element in elements_copy:
                element.raw_html = lxml_html_tostring(self.cleaner.clean_html(element.lxml))
                elements.append(element)

        return _get_first_or_list(elements, first)

    def search(self, template: str) -> Result:
        """
        Search the Element for the given Parse template.

        Args:
            template (str): The Parse template to use.

        Returns:
            Result: The result of the search.
        """
        return parse_search(template, self.html)

    def search_all(self, template: str) -> _Result:
        """
        Search the Element (multiple times) for the given parse template.

        Args:
            template (str): The Parse template to use.

        Returns:
            _Result: The result of the search.
        """
        return list(findall(template, self.html))

    @property
    def links(self) -> _Links:
        """All found links on page, in as-is form."""

        def gen():
            for link in self.find_all('a'):
                with contextlib.suppress(KeyError):
                    href = link.attrs['href'].strip()
                    if (
                        href
                        and not (href.startswith('#') and self.skip_anchors)
                        and not href.startswith(('javascript:', 'mailto:'))
                    ):
                        yield href

        return set(gen())

    def _make_absolute(self, link):
        """Makes a given link absolute."""

        # Parse the link with stdlib.
        parsed = urlparse(link)._asdict()

        # If link is relative, then join it with base_url.
        if not parsed['netloc']:
            return urljoin(self.base_url, link)

        # Link is absolute; if it lacks a scheme, add one from base_url.
        if not parsed['scheme']:
            parsed['scheme'] = urlparse(self.base_url).scheme

            # Reconstruct the URL to incorporate the new scheme.
            parsed = iter(parsed.values())
            return urlunparse(parsed)

        # Link is absolute and complete with scheme; nothing to be done here.
        return link

    @property
    def absolute_links(self) -> _Links:
        """
        All found links on page, in absolute form
        (`learn more <https://www.navegabem.com/absolute-or-relative-links.html>`_).
        """

        def gen():
            for link in self.links:
                yield self._make_absolute(link)

        return set(gen())

    @property
    def base_url(self) -> str:
        """
        The base URL for the page. Supports the ``<base>`` tag
        (`learn more <https://www.w3schools.com/tags/tag_base.asp>`_)."""

        if base := self.find_all('base', first=True):
            if result := base.attrs.get('href', '').strip():
                return result

        # Parse the url to separate out the path
        parsed = urlparse(self.url)._asdict()

        # Remove any part of the path after the last '/'
        parsed['path'] = '/'.join(parsed['path'].split('/')[:-1]) + '/'

        # Reconstruct the url with the modified path
        parsed = iter(parsed.values())
        url = urlunparse(parsed)

        return url


class Element(BaseParser):
    """
    An element of HTML.

    Args:
        element: The element from which to base the parsing upon.
        url: The URL from which the HTML originated, used for ``absolute_links``.
        default_encoding: Which encoding to default to.
    """

    __slots__ = [
        'element',
        'url',
        'skip_anchors',
        'default_encoding',
        '_encoding',
        '_html',
        '_lxml',
        '_pq',
        '_attrs',
        'session',
    ]

    def __init__(
        self,
        *,
        element,
        url: str,
        default_encoding: str = None,
        br_session: Optional[weakref.CallableProxyType] = None,
    ) -> None:
        super(Element, self).__init__(
            element=element, url=url, default_encoding=default_encoding, br_session=br_session
        )
        self.element = element
        self.tag = element.tag
        self.lineno = element.sourceline
        self._attrs = None

    def __repr__(self) -> str:
        attrs = [f'{attr}={repr(self.attrs[attr])}' for attr in self.attrs]
        return f"<Element {repr(self.element.tag)} {' '.join(attrs)}>"

    @property
    def attrs(self) -> MutableMapping:
        """R
        eturns a dictionary of the attributes of the :class:`Element <Element>`
        (`learn more <https://www.w3schools.com/tags/ref_attributes.asp>`_).
        """
        if self._attrs is None:
            self._attrs = dict(self.element.items())

            # Split class and rel up, as there are usually many of them:
            for attr in ['class', 'rel']:
                if attr in self._attrs:
                    self._attrs[attr] = tuple(self._attrs[attr].split())

        return self._attrs


class HTML(BaseParser):
    """An HTML document, ready for parsing.

    Args:
        url (str): The URL from which the HTML originated, used for ``absolute_links``.
        html (Optional[_HTML]): HTML from which to base the parsing upon.
        default_encoding (str): Which encoding to default to.

    Attributes:
        session (Union[hrequests.session.TLSSession, hrequests.browser.BrowserSession]): The session used for the HTML request.
    """

    def __init__(
        self,
        *,
        session: Optional[
            Union[hrequests.session.TLSSession, hrequests.browser.BrowserSession]
        ] = None,
        url: str = DEFAULT_URL,
        html: _HTML,
        default_encoding: str = DEFAULT_ENCODING,
    ) -> None:
        # Convert incoming unicode HTML into bytes.
        if isinstance(html, str):
            html = html.encode(DEFAULT_ENCODING)

        pq = PyQuery(html)
        super(HTML, self).__init__(
            element=pq('html') or pq.wrapAll('<html></html>')('html'),
            html=html,
            url=url,
            default_encoding=default_encoding,
            br_session=weakref.proxy(session)
            if isinstance(session, hrequests.browser.BrowserSession)
            else None,
        )
        self.session = session or hrequests.firefox.Session(temp=True)
        self.page = None
        self.next_symbol = DEFAULT_NEXT_SYMBOL

    def __repr__(self) -> str:
        return f"<HTML url={self.url!r}>"

    def next(self, fetch: bool = False, next_symbol: _NextSymbol = None) -> _Next:
        """
        Attempts to find the next page, if there is one. If ``fetch``
        is ``True`` (default), returns :class:`HTML <HTML>` object of
        next page. If ``fetch`` is ``False``, simply returns the next URL.
        """
        if next_symbol is None:
            next_symbol = DEFAULT_NEXT_SYMBOL

        def get_next():
            candidates = self.find_all('a', containing=next_symbol)

            for candidate in candidates:
                if candidate.attrs.get('href'):
                    # Support 'next' rel (e.g. reddit).
                    if 'next' in candidate.attrs.get('rel', []):
                        return candidate.attrs['href']

                    # Support 'next' in classnames.
                    for _class in candidate.attrs.get('class', []):
                        if 'next' in _class:
                            return candidate.attrs['href']

                    if 'page' in candidate.attrs['href']:
                        return candidate.attrs['href']

            try:
                # Resort to the last candidate.
                return candidates[-1].attrs['href']
            except IndexError:
                return None

        __next = get_next()
        if __next:
            url = self._make_absolute(__next)
        else:
            return None

        return self.session.get(url) if fetch else url

    def __iter__(self):
        next_ = self
        while True:
            yield next_
            try:
                next_ = next_.next(fetch=True, next_symbol=self.next_symbol).html
            except AttributeError:
                break

    def __next__(self):
        return self.next(fetch=True, next_symbol=self.next_symbol).html

    def __aiter__(self):
        return self

    async def __anext__(self):
        while True:
            url = self.next(fetch=False, next_symbol=self.next_symbol)
            if not url:
                break
            response = await self.session.get(url)
            return response.html

    def add_next_symbol(self, next_symbol):
        self.next_symbol.append(next_symbol)


def _get_first_or_list(l, first=False):
    if not first:
        return l
    try:
        return l[0]
    except IndexError:
        return None
