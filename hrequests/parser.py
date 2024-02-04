import contextlib
import weakref
from functools import partial
from typing import List, MutableMapping, Optional, Set, Union
from urllib.parse import urljoin, urlparse, urlunparse

import selectolax.lexbor
from parse import Result, findall
from parse import search as parse_search

import hrequests
from hrequests.exceptions import NotRenderedException, SelectorNotFoundException

"""
Parser structure inspired by https://github.com/psf/requests-html/blob/master/requests_html.py
Copyright 2018 Kenneth Reitz
"""


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
        html: HTML from which to base the parsing upon (optional).
        url: The URL from which the HTML originated, used for ``absolute_links``.
    """

    def __init__(
        self,
        *,
        element,
        url: str,
        br_session: Optional[weakref.CallableProxyType] = None,
    ) -> None:
        self.element = element
        self.url = url
        self.skip_anchors = True
        self.br_session = br_session

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
        'screenshot',
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
        '''
        Returns the CSS selector of the element
        '''
        node = self.element
        elems: List[str] = []
        count: int
        while True:
            count = 0
            target_id = node.mem_id
            if node.tag == 'html' or not node.parent:
                break
            for elem in node.parent.iter():
                if elem.tag == node.tag:
                    count += 1
                    if elem.mem_id == target_id:
                        elems.append(f'{node.tag}:nth-of-type({count})')
                        node = node.parent
                        break
        return ' > '.join(elems[::-1])

    @property
    def raw_html(self) -> bytes:
        """
        Bytes representation of the HTML content.
        (`learn more <http://www.diveintopython3.net/strings.html>`_).
        """
        return self.element.raw_html

    @property
    def html(self) -> str:
        """
        Unicode representation of the HTML content
        (`learn more <http://www.diveintopython3.net/strings.html>`_).
        """
        return self.element.html

    @property
    def text(self) -> str:
        """
        The text content of the
        :class:`Element <Element>` or :class:`HTML <HTML>`.
        """
        return self.get_text()

    def get_text(self, children=True, separator='\n', strip=False) -> str:
        '''
        Get the text of the element, including its children.
        Args:
            children: Whether or not to include the children.
            separator: The separator to use between the text of the children.
            strip: Whether or not to strip the text.
        '''
        return self.element.text(separator=separator, strip=strip, deep=children)

    @property
    def full_text(self) -> str:
        """
        The full text content (including links) of the
        :class:`Element <Element>` or :class:`HTML <HTML>`.
        """
        return self.element.text_content

    kwarg_map = {
        'class_': 'class',
        'for_': 'for',
        'async_': 'async',
        'accept_charset': 'accept-charset',
        'http_equiv': 'http-equiv',
    }

    def find_all(
        self,
        selector: str = "*",
        other_kwargs: Optional[MutableMapping] = None,
        *,
        containing: _Containing = None,
        first: bool = False,
        raise_exception: bool = True,
        **kwargs,
    ) -> _Find:
        """
        Given a CSS Selector, returns a list of
        :class:`Element <Element>` objects or a single one.

        Args:
            selector: CSS Selector to use.
            clean: Whether or not to sanitize the found HTML of ``<script>`` and ``<style>`` tags.
            containing: If specified, only return elements that contain the provided text.
            first: Whether or not to return just the first result.
            raise_exception: Raise an exception if no elements are found. Default is True.

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

        # convert a single containing into a list
        if isinstance(containing, str):
            containing = [containing]

        # merge kwargs into a selector string
        if kwargs or other_kwargs:
            # map kwargs that resemble built-in attributes to their css equivalents
            for k, v in self.kwarg_map.items():
                if k in kwargs:
                    kwargs[v] = kwargs.pop(k)
            if other_kwargs:  # add passed dict to kwargs
                kwargs.update(other_kwargs)
            selector = selector.rstrip() + ''.join(f'[{k}="{v}"]' for k, v in kwargs.items())

        # find elements
        if first:
            found_css = (self.element.css_first(selector),)
            # if no element was found, raise an exception or return None
            if not found_css[0]:
                if not raise_exception:
                    return None
                raise SelectorNotFoundException(
                    f"No elements were found with selector '{selector}'."
                )
        else:
            found_css = self.element.css(selector)

        elements = [
            Element(element=found, url=self.url, br_session=self.br_session) for found in found_css
        ]

        if containing:
            elements_copy = elements.copy()
            elements = [
                element
                for element in elements_copy
                if any(c.lower() in element.full_text.lower() for c in containing)
            ]
            elements.reverse()

        return _get_first_or_list(elements, first)

    def find(
        self,
        selector: str = "*",
        other_kwargs: Optional[MutableMapping] = None,
        *,
        exception_handler: Optional[callable] = None,
        containing: _Containing = None,
        **kwargs,
    ) -> _Find:
        # Wrapper around find_all with first=True.
        try:
            return self.find_all(
                selector=selector,
                other_kwargs=other_kwargs,
                containing=containing,
                first=True,
                **kwargs,
            )
        except SelectorNotFoundException:
            if exception_handler:
                return exception_handler()

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

        if base := self.find_all('base', first=True, raise_exception=False):
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
    """

    __slots__ = [
        'element',
        'url',
        'skip_anchors',
        '_attrs',
        'session',
    ]

    def __init__(
        self,
        *,
        element,
        url: str,
        br_session: Optional[weakref.CallableProxyType] = None,
    ) -> None:
        super().__init__(element=element, url=url, br_session=br_session)
        self.element = element
        self.tag = element.tag
        self._attrs = None

    def __repr__(self) -> str:
        attrs = [f'{attr}={repr(self.attrs[attr])}' for attr in self.attrs]
        return f"<Element {repr(self.element.tag)} {' '.join(attrs)}>"

    @property
    def attrs(self) -> MutableMapping:
        """
        Returns a dictionary of the attributes of the :class:`Element <Element>`
        (`learn more <https://www.w3schools.com/tags/ref_attributes.asp>`_).
        """
        if self._attrs is None:
            self._attrs = self.element.attributes

            # Split class and rel up, as there are usually many of them:
            for attr in ['class', 'rel']:
                if attr in self._attrs:
                    self._attrs[attr] = tuple(self._attrs[attr].split())

        return self._attrs

    def __getattr__(self, name):
        if name in self.attrs:
            return self.attrs[name]
        if name in self.kwarg_map:
            return self.attrs[self.kwarg_map[name]]
        return super().__getattr__(name)


class HTML(BaseParser):
    """An HTML document, ready for parsing.

    Args:
        url (str): The URL from which the HTML originated, used for ``absolute_links``.
        html (Optional[_HTML]): HTML from which to base the parsing upon.

    Attributes:
        session (Union[hrequests.session.TLSSession, hrequests.browser.BrowserSession]): The session used for the HTML request.
    """

    def __init__(
        self,
        *,
        session: Optional[
            Union['hrequests.session.TLSSession', 'hrequests.browser.BrowserSession']
        ] = None,
        url: str = DEFAULT_URL,
        html: _HTML,
    ) -> None:
        # Convert incoming unicode HTML into bytes.
        element = selectolax.lexbor.LexborHTMLParser(html)
        super().__init__(
            element=element,
            url=url,
            br_session=(
                weakref.proxy(session)
                if hasattr(hrequests, 'browser')  # if the browser module is imported
                and isinstance(
                    session, hrequests.browser.BrowserSession
                )  # and session is a BrowserSession
                else None
            ),
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
