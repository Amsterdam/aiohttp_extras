"""Asynchronous JSON serializer.

This module defines a method `encode`.

"""

import re
import logging
import inspect
import collections
import collections.abc

from yarl import URL
from aiohttp import web

from . import _view

_logger = logging.getLogger(__name__)


JSON_DEFAULT_CHUNK_SIZE = 1024 * 1024
IM_A_DICT = {}
_INFINITY = float('inf')

_ESCAPE = re.compile(r'[\x00-\x1f\\"\b\f\n\r\t]')
_ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for i in range(0x20):
    _ESCAPE_DCT.setdefault(chr(i), '\\u{0:04x}'.format(i))


def _replace(match):
    return _ESCAPE_DCT[match.group(0)]


def _encode_string(s):
    return '"' + _ESCAPE.sub(_replace, s) + '"'


def _encode_float(o, allow_nan=False):
    # Check for specials.  Note that this type of test is processor
    # and/or platform-specific, so do tests which don't depend on the
    # internals.

    if o != o:
        text = 'NaN'
    elif o == _INFINITY:
        text = 'Infinity'
    elif o == -_INFINITY:
        text = '-Infinity'
    else:
        return repr(o)

    if not allow_nan:
        raise ValueError(
            "Out of range float values are not JSON compliant: " +
            repr(o))

    return text


async def _encode_list(obj, stack):
    if id(obj) in stack:
        raise ValueError("Cannot serialize cyclic data structure.")
    stack.add(id(obj))
    try:
        first = True
        for item in obj:
            if first:
                yield '['
                first = False
            else:
                yield ','
            async for s in _encode(item, stack):
                yield s
        if first:
            yield '[]'
        else:
            yield ']'
    finally:
        stack.remove(id(obj))


async def _encode_async_generator(obj, stack):
    if id(obj) in stack:
        raise ValueError("Cannot serialize cyclic data structure.")
    stack.add(id(obj))
    try:
        first = True
        is_dict = False
        async for item in obj:
            if first:
                if item is IM_A_DICT:
                    is_dict = True
                    continue
                yield '{' if is_dict else '['
                first = False
            else:
                yield ','
            if is_dict:
                if not isinstance(item[0], str):
                    message = "Dictionary key is not a string: '%r'"
                    raise ValueError(message % repr(item[0]))
                yield _encode_string(item[0]) + ':'
                async for s in _encode(item[1], stack):
                    yield s
            else:
                async for s in _encode(item, stack):
                    yield s
        if first:
            yield '[]'
        else:
            yield '}' if is_dict else ']'
    finally:
        stack.remove(id(obj))


async def _encode_dict(obj, stack):
    if id(obj) in stack:
        raise ValueError("Cannot serialize cyclic data structure.")
    stack.add(id(obj))
    try:
        first = True
        for key, value in obj.items():
            if not isinstance(key, str):
                message = "Dictionary key is not a string: '%r'"
                raise ValueError(message % repr(key))
            if first:
                yield '{' + _encode_string(key) + ':'
                first = False
            else:
                yield ',' + _encode_string(key) + ':'
            async for s in _encode(value, stack):
                yield s
        if first:
            yield '{}'
        else:
            yield '}'
    finally:
        stack.remove(id(obj))


async def _encode(obj, stack):
    """

    :param any obj:
    :param set stack:

    """
    if isinstance(obj, URL):
        yield _encode_string(str(obj))
    elif isinstance(obj, _view.View):
        try:
            obj = await obj.to_dict()
        except web.HTTPException as e:
            _logger.error("Unexpected exception", exc_info=e, stack_info=True)
            obj = {
                '_links': {'self': {'href': 'http://error.com/'}},
                '_status': e.status_code
            }
            if e.text is not None:
                obj['description'] = e.text
        async for s in _encode_dict(obj, stack):
            yield s
    elif isinstance(obj, str):
        yield _encode_string(obj)
    elif obj is None:
        yield 'null'
    elif obj is True:
        yield 'true'
    elif obj is False:
        yield 'false'
    elif isinstance(obj, float):
        yield _encode_float(obj)
    elif isinstance(obj, int):
        yield str(obj)
    elif isinstance(obj, collections.abc.Mapping):
        async for s in _encode_dict(obj, stack):
            yield s
    elif isinstance(obj, collections.abc.Iterable):
        async for s in _encode_list(obj, stack):
            yield s
    elif inspect.isasyncgen(obj):
        async for s in _encode_async_generator(obj, stack):
            yield s
    elif hasattr(obj, '__str__'):
        message = "Not sure how to serialize object of class %s:\n" \
                  "%s\nDefaulting to str()."
        _logger.warning(message, type(obj), repr(obj))
        yield _encode_string(str(obj))
    else:
        message = "Don't know how to serialize object of class %s:\n" \
                  "%s"
        _logger.error(message, type(obj), repr(obj))
        yield 'null'


async def json_encode(obj, chunk_size=JSON_DEFAULT_CHUNK_SIZE):
    """Asynchronous JSON serializer.

    :param any obj:
    :param int chunk_size: The size of chunks to be yielded.
    :rtype: collections.AsyncIterable

    """
    buffer = bytearray()
    async for b in _encode(obj, set()):
        buffer += b.encode()
        while len(buffer) >= chunk_size:
            yield buffer[:chunk_size]
            del buffer[:chunk_size]
    if len(buffer) > 0:
        yield buffer
