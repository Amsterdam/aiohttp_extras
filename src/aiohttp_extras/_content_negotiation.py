# language=rst
"""

To support *content type negotiation* in GET requests, this package provides
method :meth:`best_content_type`.  Additionally, it provides a mixin
:class:`ContentNegotiationMixin` to be used when inheriting from
:class:`aiohttp.web.View` .

"""
import logging
import typing as T
import abc

from aiohttp import web

_logger = logging.getLogger(__name__)

_BCT_CACHED_VALUE_KEY = 'aiohttp_extras.best_content_type'


# ┏━━━━━━━━━━━━━━━━━━━━━┓
# ┃ Content Negotiation ┃
# ┗━━━━━━━━━━━━━━━━━━━━━┛

def best_content_type(
    request: web.Request,
    available_content_types: T.List[str]
) -> str:
    # language=rst
    """The best matching content type.

    Returns:
        The best content type to use for the HTTP response, given a certain
        ``request`` and a list of ``available_content_types``.

    Parameters:
        request (aiohttp.web.Request): the request from which to extract an
            ``Accept:`` header.
        available_content_types: an ordered list of available content types,
            ordered by quality, best quality first.

    Raises:
        web.HTTPNotAcceptable: if none of the available content types are
            acceptable by the client. See :ref:`aiohttp web exceptions
            <aiohttp-web-exceptions>`.

    Example::

        AVAILABLE = [
            'foo/bar',
            'foo/baz; charset="utf-8"'
        ]
        def handler(request):
            bct = best_content_type(request, AVAILABLE)

    """
    if 'ACCEPT' not in request.headers:
        return available_content_types[0]
    accept = ','.join(request.headers.getall('ACCEPT'))
    acceptable_content_types = dict()
    for acceptable in accept.split(','):
        try:
            main, sub = acceptable.split(';', 2)[0].strip().split('/', 2)
        except ValueError:
            raise web.HTTPBadRequest(text="Malformed Accept: header") from None
        if main not in acceptable_content_types:
            acceptable_content_types[main] = set()
        acceptable_content_types[main].add(sub)
    # Try to find a matching 'main/sub' or 'main/*':
    for available in available_content_types:
        main, sub = available.split(';', 2)[0].strip().split('/', 2)
        if main in acceptable_content_types:
            subs = acceptable_content_types[main]
            if sub in subs or '*' in subs:
                return available
    if '*' in acceptable_content_types and '*' in acceptable_content_types['*']:
        return available_content_types[0]
    # Darn, none of our content types are acceptable to the client:
    body = ",".join(available_content_types).encode('ascii')
    raise web.HTTPNotAcceptable(
        body=body,
        content_type='text/plain; charset="US-ASCII"'
    )


class ContentNegotiationMixin(abc.ABC):
    # language=rst
    """`View <aiohttp.web.View>` mixin that helps with content negotiation.

    This mixin provides a property :attr:`best_content_type`.

    Classes that use this mixin *must* provide a class attribute
    ``AVAILABLE_CONTENT_TYPES``, or an AssertionError will be raised on subclass
    definition.  This attribute must contain a list of content types that
    instances of this class are able to produce.

    Example::

        class MyView(aiohttp_extras.View, aiohttp_extras.ContentNegatiationMixin):
            AVAILABLE_CONTENT_TYPES = ...

            def get(self):
                ...
                response.content_type = self.best_content_type

    """

    def __init_subclass__(cls):
        assert hasattr(cls, 'AVAILABLE_CONTENT_TYPES')

    @property
    def best_content_type(self) -> str:
        # language=rst
        """The best content type to represent this resource.

        This property is a shortcut for function :func:`best_content_type`.
        Ie. the following two lines of code are equivalent::

            bct = my_view.best_content_type
            bct = best_content_type(my_view.request, my_view.AVAILABLE_CONTENT_TYPES)

        """
        if _BCT_CACHED_VALUE_KEY not in self.request:
            self.request[_BCT_CACHED_VALUE_KEY] = best_content_type(
                self.request, self.AVAILABLE_CONTENT_TYPES
            )
        return self.request[_BCT_CACHED_VALUE_KEY]
