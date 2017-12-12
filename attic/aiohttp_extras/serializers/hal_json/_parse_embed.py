"""Middleware that parses the 'embed=...' query parameter."""

import re
import logging
from collections import deque
import typing as T

from aiohttp import web

_logger = logging.getLogger(__name__)


_EMBED_TOKEN = re.compile(r',?[a-z_]\w*|\(|,?\)', flags=re.IGNORECASE)
"""Used only by :func:`_tokenize_embed`."""


def _tokenize_embed(s: str):
    # language=rst
    """Tokenizer for the `embed` query parameter.

    Used exclusively by :func:`parse_embed`.

    Possible tokens are:

    identifiers
        always start with an underscore '_' or an alphabetical character,
        followed by zero or more underscores, alphabetical characters or digits.
        Examples: ``foo``, ``_BAR``, ``f00_123``
    punctuation characters
        either ``(`` or ``)``

    For each token found, this generator yields a tuple ``(token, pos)`` with
    the token string and the position at which the token was found.

    Example::

        >>> list(_tokenize_embed('foo(bar,baz)'))
        [('foo', 0), ('(', 3), ('bar', 4), ('baz', 8), (')', 11)]

    Yields:
        tuple(token: str, pos: int)

    Raises:
        web.HTTPBadRequest: if a syntax error is detected.

    Todo:
        Write additional tests, other than the "happy path".

    """
    pos = 0
    for match in _EMBED_TOKEN.finditer(s):
        if match.start() != pos:
            raise web.HTTPBadRequest(
                text="Syntax error in query parameter 'embed' at '%s'" % s[pos:]
            )
        token = match[0]
        if token[:1] == ',':
            token = token[1:]
        yield token, pos
        pos = match.end()
    if pos != len(s) and s[pos:] != ',':
        raise web.HTTPBadRequest(
            text=f"Syntax error in query parameter 'embed' at '{s[pos:]}'"
        )


def parse_embed_old(embed: str) -> T.Dict[str, T.Optional[str]]:
    # language=rst
    """Parser for the `embed` query parameter.

    Example:

        >>> parse_embed('foo(bar,baz),bar')
        {'foo': 'bar,baz', 'bar': None}

    Raises:
        web.HTTPBadRequest: if a syntax error is detected.

    Todo:
        Write additional tests, other than the "happy path".

    """
    result = {}
    if len(embed) == 0:
        return result
    seen = deque()
    seen.appendleft(set())
    sub_query_info = None
    current = None
    for token, pos in _tokenize_embed(embed):
        rest = embed[pos:]
        if token == '(':
            if current is None:
                raise web.HTTPBadRequest(
                    text=f"Unexpected opening parenthesis in query parameter 'embed' at '{rest}'"
                )
            if len(seen) == 1:
                sub_query_info = (current, pos + 1)
            seen.appendleft(set())
            current = None
        elif token == ')':
            seen.popleft()
            if len(seen) == 0:
                raise web.HTTPBadRequest(
                    text=f"Unmatched closing parenthesis in query parameter 'embed' at '{rest}'"
                )
            if len(seen) == 1:
                result[sub_query_info[0]] = embed[sub_query_info[1]:pos]
        else:
            if token in seen[0]:
                message = f"Link relation '{token}' mentioned more than once in query parameter 'embed' at '{rest}'"
                raise web.HTTPBadRequest(text=message)
            if token in ('self',):
                message = f"Link relation '{token}' can not be embedded"
                raise web.HTTPBadRequest(text=message)
            seen[0].add(token)
            current = token
            if len(seen) == 1:
                result[token] = None
    if len(seen) > 1:
        raise web.HTTPBadRequest(
            text="Unmatched opening parenthesis in query parameter 'embed' at position %d" % sub_query_info[1]
        )
    return result


def parse_embed(embed: str) -> T.Dict[str, T.Optional[dict]]:
    # language=rst
    """Parser for the ``embed`` query parameter.

    Example:

        >>> parse_embed('foo(bar,baz),bar')
        {'foo': {'bar': None, 'baz': None}, 'bar': None}

    Raises:
        web.HTTPBadRequest: if a syntax error is detected.

    """
    result = {}
    if len(embed) == 0:
        return result
    cursor = deque([result])
    seen = deque([set()])
    current_token = None
    for token, pos in _tokenize_embed(embed):
        rest = embed[pos:]
        if token == '(':
            if current_token is None:
                raise web.HTTPBadRequest(
                    text=f"Unexpected opening parenthesis in query parameter 'embed' at '{rest}'"
                )
            seen.appendleft(set())
            cursor.appendleft(cursor[0][current_token])
            current_token = None
        elif token == ')':
            seen.popleft()
            cursor.popleft()
            if len(seen) == 0:
                raise web.HTTPBadRequest(
                    text=f"Unmatched closing parenthesis in query parameter 'embed' at '{rest}'"
                )
        else:
            if token in seen[0]:
                message = f"Link relation '{token}' mentioned more than once in query parameter 'embed' at '{rest}'"
                raise web.HTTPBadRequest(text=message)
            if token in ('self',):
                message = f"Link relation '{token}' can not be embedded"
                raise web.HTTPBadRequest(text=message)
            seen[0].add(token)
            current_token = token
            cursor[0][current_token] = {}
    if len(seen) > 1:
        raise web.HTTPBadRequest(
            text="Unmatched opening parenthesis in query parameter 'embed'"
        )
    return result


def to_string(embed: T.Dict[str, dict]) -> str:
    # language=rst
    """Serializer for the ``embed`` query parameter.

    Given the output of :func:`parse_embed`, this method serializes back to the
    query parameter string::

        >>> parse_embed(to_string(some_embed_dict)) == some_embed_dict
        True

    """
    def to_string_recursive(embed):
        if len(embed) == 0:
            return ''
        return '(' + ','.join(
            key + to_string_recursive(value) for key, value in embed.items()
        ) + ')'
    return ','.join(
        key + to_string_recursive(value) for key, value in embed.items()
    )
