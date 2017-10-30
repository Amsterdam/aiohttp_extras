# language=rst
"""

Overview
========

This module provides support for conditional request handling, based on ETags,
as defined in :rfc:`7232`.

There are two use cases for conditional requests:

1.  For safe methods (ie. ``OPTIONS``, ``GET``, and ``HEAD``), conditional
    requests can be used by caching clients — including caching forward proxies
    — to download the resource representation only if it has changed since the
    cached version.  In this case, the client adds an ``If-None-Match:`` header
    and includes the ETag(s) of the cached representation(s).
2.  For unsafe methods (ie. ``DELETE``, ``PATCH``, ``POST``, and ``PUT``),
    conditional requests can be used to avoid *lost updates*.  For this use
    case, there are two scenarios:

    a.  When performing an unsafe request, the client adds an ``If-Match:``
        header with the ETag of the resource as last seen by the client.  This
        guarantees that the client doesn't accidentally delete or overwrite a
        newer version of the resource.
    b.  When performing a ``PUT`` request with the intention of creating a new
        resource, the client adds an ``If-None-Match: *`` header to assert that
        no resource yet exists at the given request URI.

Note:
      Even if ETags is prohibitively expensive for your resources, this module
      can still handle conditional requests based on the *presence* or *absence*
      of your (dynamic) resource.  In this case, only use case 2.b. is really
      supported.

Todo:
    Add support for conditional request handling based on the ``Last-Modified:``


ETagMixin
---------

If you want conditional request handling for one of your views, use
:class:`ETagMixin`, and implement abstract method :meth:`etag <ETagMixin.etag>`.
The mixin provides a method :meth:`assert_preconditions
<ETagMixin.assert_preconditions>`, which gets called automatically by the
framework for ``GET`` and ``HEAD`` requests. For other requests, you need to
call this method yourself at some appropriate moment during request handling.


Helpers for ETag creation
-------------------------

To facilitate the creation of valid ETags for your resources, this library provides the following helpers:

-   :func:`etaggify` converts a string to a syntactically valid ETag.
-   :func:`etag_from_int` and :func:`etag_from_float` convert integers and
    floating point values to very compact ETags.
-   :class:`ETagGenerator` can create a unique ETag from any (complex) value,
    using canonical JSON encoding and SHA3_224 hashing.


API documentation
=================

"""

import abc
import logging
import typing as T
import re
import base64
import struct
import json
import hashlib
from collections.abc import Mapping

from aiohttp import web

_logger = logging.getLogger(__name__)

_ETAGS_PATTERN = re.compile(
    r'\s*(?:W/)?"[\x21\x23-\x7e\x80-\xff]+"(?:\s*,\s*(?:W/)?"[\x21\x23-\x7e\x80-\xff]+")*'
)
_ETAG_ITER_PATTERN = re.compile(
    r'((?:W/)?"[\x21\x23-\x7e\x80-\xff]+")'
)
_STAR = '*'
_STAR_TYPE = str
_HTTP_UNSAFE_METHODS = {'DELETE', 'PATCH', 'POST', 'PUT'}
_VALID_ETAG_CHARS = re.compile(r'[\x21\x23-\x7e\x80-\xff]+')
_IF_MATCH = 'If-Match'
_IF_NONE_MATCH = 'If-None-Match'


def _parse_if_header(request: web.Request, header_name: str) -> T.Union[None, T.Set[str], _STAR_TYPE]:
    # language=rst
    """Parses ``If-(None-)Match:`` request headers.

    Args:
        request:
        header_name:  either ``'If-Match'`` or ``'If-None-Match'``

    Returns:
        T.Union[None, T.Set, _STAR_TYPE]: ``None`` if the header is not present
        in the request.  Otherwise a `set` of ETags or string literal
        ``"*"`` as found in the request header.

    Raises:
        web.HTTPBadRequest: If the request header is malformed.

    Warning:
        This parser allows an ``If-(None-)Match:`` request header with an empty
        value.  This is not :rfc:`7232` compliant, and a work-around for a bug
        in Swagger-UI.

    """
    if header_name not in request.headers:
        return None
    header = ','.join(request.headers.getall(header_name))
    if header == '':
        return None
    if header == _STAR:
        return _STAR
    if not _ETAGS_PATTERN.fullmatch(header):
        raise web.HTTPBadRequest(
            text="Syntax error in request header If-Match: %s" % header
        )
    return { match[1] for match in _ETAG_ITER_PATTERN.finditer(header) }


def _match_etags(etag: str, etags: T.Iterable[str], allow_weak: bool) -> bool:
    # language=rst
    """ETag comparison according to :rfc:`7232`.

    See :rfc:`section 2.3.2 <7232#section-2.3.2>` for a detailed explanation of
    *weak* vs. *strong comparison*.

    Parameters:
        etag:
        etags:
        allow_weak: if ``True``, this function uses the *weak comparison*
            algorithm;  otherwise *strong comparison* is used.

    Returns:
        ``True`` if ``etag`` matches against any ETag in ``etags``.

    """
    if not allow_weak:
        return str(etag)[0] == '"' and etag in etags
    if etag[0:2] == 'W/':
        etag = etag[2:]
    return etag in etags or ('W/' + etag) in etags


def _assert_if_match(request: web.Request,
                     etag: T.Union[None, bool, str],
                     require: bool,
                     deny_star: bool,
                     allow_weak: bool):
    # language=rst
    """

    Raises:
        web.HTTPPreconditionRequired:
            If parameter `require` is ``True`` and no precondition was provided
            by the client.
        web.HTTPBadRequest: Either

            -   the request header is syntactically incorrect, or
            -   parameter `deny_star` is ``True`` and the client provided an
                asterisk instead of a valid ETag.
        web.HTTPPreconditionFailed:

    """
    etags = _parse_if_header(request, _IF_MATCH)

    if etags is None:
        if require:
            raise web.HTTPPreconditionRequired(
                text=_IF_MATCH
            )
        return
    if etags is _STAR:
        if deny_star:
            raise web.HTTPBadRequest(
                text='If-Match: requires a valid ETag for this request.'
            )
        if etag is None or etag is False:
            raise web.HTTPPreconditionFailed(text=_IF_MATCH)
        return
    # From here on, `etags` can only be a set().
    if etag is True:
        raise web.HTTPPreconditionFailed(
            text="Resource doesn't have an ETag."
        )
    if (
        etag is True          # the resource exists, but doesn't have a specific ETag
        or etag is False      # the resource doesn't exist
        or etag is None       # the resource doesn't exist
        # the resource has a different ETag:
        or not _match_etags(etag, etags, allow_weak)
    ):
        raise web.HTTPPreconditionFailed(text=_IF_MATCH)


def _assert_if_none_match(request: web.Request,
                          etag: T.Union[None, bool, str],
                          require: bool,
                          allow_weak: bool):
    # language=rst
    """

    Todo:
        Evert lammerts schreef: Documenteren. Ik vind _assert_if_none_match niet
        makkelijk te lezen zonder docs voor de parameters. Bv: etag heeft als
        type None, bool, of str. En if etag is True: PreconditionFailed. Die
        semantiek is vast logisch in context maar niet op zichzelf.

    The If-None-Match: header is used in two scenarios:

    1.   GET requests by a caching client. In this case, the client will
         normally provide a list of (cached) ETags.
    2.   PUT requests, where the client intends to create a new resource and
         wants to avoid overwriting an existing resource. In this case, the
         client will normally provide only the asterisk "*" character.

    Raises:
        web.HTTPBadRequest:
            If the request header is syntactically incorrect.
        web.HTTPPreconditionRequired:
            If parameter `require` is ``True`` and no precondition was provided
            by the client.
        web.HTTPPreconditionFailed:
            If the precondition failed and the request is *unsafe*.
        web.HTTPNotModified:
            If the precondition failed and the request is *safe*.

    """
    etags = _parse_if_header(request, _IF_NONE_MATCH)

    if require and etags is None:
        raise web.HTTPPreconditionRequired(text=_IF_NONE_MATCH)
    if etags is None or etag is False or etag is None:
        return
    if etags is _STAR:
        raise web.HTTPPreconditionFailed(text=_IF_NONE_MATCH)
    # From here on, we know that etags is a set of strings.
    if etag is True:
        raise web.HTTPPreconditionFailed(
            text="Resource doesn't have an ETag."
        )
    # From here on, we know that etag is a string:
    if _match_etags(etag, etags, allow_weak):
        if request.method in {'GET', 'HEAD'}:
            raise web.HTTPNotModified()
        else:
            raise web.HTTPPreconditionFailed(text=_IF_NONE_MATCH)


def assert_preconditions(request: web.Request,
                         etag: T.Union[None, bool, str],
                         require_if_match:      bool=False,
                         deny_if_match_star:    bool=False,
                         require_if_none_match: bool=False,
                         allow_weak:            bool=False):
    # language=rst
    """

    Parameters:
        request:
            the current HTTP request
        etag:
            any value produced by :meth:`ETagMixin.etag`
        require_if_match:
            set ``True`` to assert the presence of an ``If-Match:`` request
            header
        deny_if_match_star:
            if ``True``, raises :exc:`web.HTTPBadRequest` if the client sends an
            ``If-Match: *`` request header.  This forces the client to send a
            specific valid ETag.
        require_if_none_match:
            set ``True`` to assert the presence of an ``If-None-Match:`` request
            header
        allow_weak:
            set ``True`` to allow weak ETag comporisons.

    Raises:
        see :func:`_assert_if_match` and :func:`_assert_if_none_match`

    Warning:
        Parameter `allow_weak` is not yet implemented.  If set to ``True``, a
        :exc:`ValueError` is raised.

    """
    _assert_if_match(request, etag, require_if_match, deny_if_match_star, allow_weak)
    _assert_if_none_match(request, etag, require_if_none_match, allow_weak)


def etaggify(v: str, weak: bool=False) -> str:
    # language=rst
    """Generates a syntactically valid ETag.

    Args:
        v: The string to use inside the ETag.
        weak: if ``True``, a weak ETag is created, ie. an ETag that starts with
            ``W/``.

    >>> etaggify('foo')
    '"foo"'
    >>> etaggify('bar', weak=True)
    'W/"bar"'

    """
    assert _VALID_ETAG_CHARS.fullmatch(v)
    weak = 'W/' if weak else ''
    return weak + '"' + v + '"'


def etag_from_int(value: int, weak: bool=False) -> str:
    # language=rst
    """Translates an integer to an ETag string."""
    if -0x80 <= value < 0x80:
        format = 'b'
    elif -0x8000 <= value < 0x8000:
        format = 'h'
    elif -0x80000000 <= value < 0x80000000:
        format = 'l'
    else:
        format = 'q'
    return etaggify(
        base64.urlsafe_b64encode(struct.pack(format, value)).decode(),
        weak
    )


def etag_from_float(value: float, weak=False) -> str:
    # language=rst
    """Translates a float to an ETag string."""
    return etaggify(
        base64.urlsafe_b64encode(struct.pack('d', value)).decode(),
        weak
    )


def _json_dumps_default(value):
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError()


class ETagGenerator:
    # language=rst
    """Helper class to facilitate creation of ETags.

    Example::

        some_internal_state = ...
        some_other_internal_state = ...

        etag_generator = ETagGenerator()
        etag_generator.update(some_internal_state)
        etag_generator.update(some_other_internal_state)

        etag = etag_generator.etag

    The same, but shorter:

        some_internal_state = ...
        some_other_internal_state = ...
        etag = ETagGenerator(some_internal_state, some_other_internal_state).etag

    """
    def __init__(self, *args):
        self._hash = hashlib.sha3_224()
        for arg in args:
            self.update(arg)

    def update(self, v: T.Any):
        # language=rst
        """Incrementally feeds state to this etag generator.

        Parameters:
            v: any value that can be serialized to JSON with Python's default json encoder.

        Returns:
            ETagGenerator: self

        """
        # Option "sort_keys=True" is here to make the JSON serialization
        # deterministic. This guarantees that you'll get the same ETag every
        # time you use ETagGenerator en the same dictionary.
        self._hash.update(
            json.dumps(v, ensure_ascii=False, sort_keys=True, default=_json_dumps_default).encode()
        )
        return self

    @property
    def etag(self, weak: bool=False):
        # language=rst
        """Returns an ETag, based on the state fed to :meth:`update`.

        Parameters:
            weak: indicates if a weak ETag should be returned.  See :rfc:`2616`.

        Returns:
            str: A valid ETag, that can be put into an ``ETag:`` header.

        """
        return etaggify(
            base64.urlsafe_b64encode(self._hash.digest()).decode(),
            weak
        )


class ETagMixin(abc.ABC):
    # language=rst
    """

    This View mixin provides support for conditional request handling based on ETags.

    """

    @abc.abstractmethod
    async def etag(self) -> T.Union[None, bool, str]:
        # language=rst
        """

        Return values have the following semantics:

        ``True``
            Resource exists but doesn't support ETags
        ``False``
            Resource doesn't exist and doesn't support ETags
        ``None``
            Resource doesn't exist and supports ETags.
        a valid ETag string
            Resource exists and supports ETags.

        See Also:
            -   Class :class:`ETagGenerator` can help you generate unique ETags.
            -   Function :func:`etaggify` can help you generate syntactically
                valid ETags.

        """

    async def assert_preconditions(self,
                                   require_if_match:      bool=False,
                                   deny_if_match_star:    bool=False,
                                   require_if_none_match: bool=False,
                                   allow_weak:            bool=False):
        # language=rst
        """

        Parameters:
            require_if_match:
                set ``True`` to assert the presence of an ``If-Match:`` request
                header
            deny_if_match_star:
                if ``True``, raises :exc:`web.HTTPBadRequest` if the client sends an
                ``If-Match: *`` request header.  This forces the client to send a
                specific valid ETag.
            require_if_none_match:
                set ``True`` to assert the presence of an ``If-None-Match:`` request
                header
            allow_weak:
                set ``True`` to allow weak ETag comporisons.

        Raises:
            see :func:`_assert_if_match` and :func:`_assert_if_none_match`

        Warning:
            Parameter `allow_weak` is not yet implemented.  If set to ``True``, a
            :exc:`ValueError` is raised.

        """
        etag = await self.etag()
        _assert_if_match(
            self.request,
            etag,
            require_if_match,
            deny_if_match_star,
            allow_weak
        )
        _assert_if_none_match(
            self.request,
            etag,
            require_if_none_match,
            allow_weak
        )
