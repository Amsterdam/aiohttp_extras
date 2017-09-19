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

ETagType = T.Union[str, bool, None]
_ETAGS_PATTERN = re.compile(
    r'\s*(?:W/)?"[\x21\x23-\x7e\x80-\xff]+"(?:\s*,\s*(?:W/)?"[\x21\x23-\x7e\x80-\xff]+")*'
)
_ETAG_ITER_PATTERN = re.compile(
    r'((?:W/)?"[\x21\x23-\x7e\x80-\xff]+")'
)
_STAR = '*'
_STAR_TYPE = str
_HTTP_UNSAFE_METHODS = {'DELETE', 'PATCH', 'POST', 'PUT'}
VALID_ETAG_PATTERN = re.compile(r'(?:W/)?"[\x21\x23-\x7e\x80-\xff]+"')


def _parse_if_header(request: web.Request, header_name: str) -> T.Union[None, T.Set, _STAR_TYPE]:
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
    return set({
        match[1] for match in _ETAG_ITER_PATTERN.finditer(header)
    })


def _assert_if_match(request: web.Request, etag: T.Union[None, bool, str], require: bool):
    # The If-Match: header is commonly used in non-safe HTTP requests to prevent
    # lost update problems.
    etags = _parse_if_header(request, 'If-Match')

    if etags is None:
        if require:
            raise web.HTTPPreconditionRequired(
                text='If-Match'
            )
        return
    if etags is _STAR:
        if etag is None or etag is False:
            raise web.HTTPPreconditionFailed()
        if etag is True or require is False:
            return
        raise web.HTTPPreconditionRequired(
            text='If-Match: * is too generic for this resource.'
        )
    # From here on, `etags` can only be a set().
    if etag is True or etag is False:
        raise web.HTTPPreconditionFailed(
            text="Resource doesn't support If-Match header."
        )
    # From here on, `etag` can only be `None` or a valid ETag string:
    if etag is None:
        raise web.HTTPNotFound()
    if etag not in etags:
        raise web.HTTPPreconditionFailed()


def _assert_if_none_match(request: web.Request, etag: T.Union[None, bool, str], require: bool):
    # The If-None-Match: header is used in two scenarios:
    # 1. GET requests by a caching client. In this case, the client will
    #    normally provide a list of (cached) ETags.
    # 2. PUT requests, where the client intends to create a new resource and
    #    wants to avoid overwriting an existing resource. In this case, the
    #    client will normally provide only the asterisk "*" character.
    etags = _parse_if_header(request, 'If-None-Match')
    if require and etags is None:
        raise web.HTTPPreconditionRequired(
            text='If-None-Match'
        )
    if etags is None or etag is False or etag is None:
        return
    if etags is _STAR:
        raise web.HTTPPreconditionFailed()
    # From here on, we know that etags is a set of strings.
    if etag is True:
        raise web.HTTPPreconditionFailed(
            text="Resource doesn't support ETags."
        )
    # From here on, we know that etag is a string:
    if etag in etags:
        if request.method in {'GET', 'HEAD'}:
            raise web.HTTPNotModified()
        else:
            raise web.HTTPPreconditionFailed()


def assert_preconditions(request: web.Request, etag: T.Union[None, bool, str],
                         require_if_match=False, require_if_none_match=False):
    _assert_if_match(request, etag, require_if_match)
    _assert_if_none_match(request, etag, require_if_none_match)


def etaggify(v: str, weak: bool) -> str:
    assert '"' not in v
    weak = 'W/' if weak else ''
    return weak + '"' + v + '"'


def etag_from_int(value: int, weak=False) -> str:
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

    Example:
        class SomeWebResource(View):
            def etag(self):
                return ETagGenerator().update(self.state).etag()

    """
    def __init__(self):
        self._hash = hashlib.sha3_224()

    def update(self, v: T.Any):
        # language=rst
        """Incrementally feeds state to this etag generator.

        Parameters:
            v: any value that can be serialized to JSON with Python's default json encoder.

        Returns:
            ETagGenerator: self

        Example:
            etag_generator = ETagGenerator()
            etag_generator.update(some_state)
            etag_generator.update(some_more_state)
            print(etag_generator.etag())

        """
        self._hash.update(
            json.dumps(v, ensure_ascii=False, sort_keys=True, default=_json_dumps_default).encode()
        )
        return self

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
