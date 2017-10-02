"""Middleware that parses the 'embed=...' query parameter."""

import re
import logging
from collections import deque
import typing as T

from aiohttp import web

_logger = logging.getLogger(__name__)


_EMBED_TOKEN = re.compile(r',?[a-z_]\w*|\(|,?\)', flags=re.IGNORECASE)
"""Used only by :func:`_tokenize_embed`."""

MAX_QUERY_DEPTH = 3
# language=rst
"""Maximum query depth

To mitigate DoS-attack potential, the maximum embedding depth is limited.  You can change the maximum embedding depth from your code::

    import rest_utils
    
    rest_utils.MAX_QUERY_DEPTH = 5
    
"""


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

        list(_tokenize_embed('foo(bar,baz)'))
        >>> [('foo', 0), ('(', 3), ('bar', 4), ('baz', 8), (')', 11)]

    :yields: tuple(token: str, pos: int)
    :raises: :ref:`HTTPBadRequest <aiohttp-web-exceptions>` if a syntax error is
        detected.

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
    if pos != len(s):
        raise web.HTTPBadRequest(
            text="Syntax error in query parameter 'embed' at '%s'" % s[pos:]
        )


def parse_embed(embed: str) -> T.Dict[str, T.Optional[str]]:
    # language=rst
    """Parser for the `embed` query parameter.

    Example::

        >>> parse_embed('foo(bar,baz),bar')
        {'foo': 'bar,baz', 'bar': None}

    :raises: :ref:`HTTPBadRequest <aiohttp-web-exceptions>` if a syntax error is
        detected.

    """
    assert MAX_QUERY_DEPTH > 0
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
                    text="Unexpected opening parenthesis in query parameter 'embed' at '%s'" % rest
                )
            if len(seen) == 1:
                sub_query_info = (current, pos + 1)
            seen.appendleft(set())
            current = None
        elif token == ')':
            seen.popleft()
            if len(seen) == 0:
                raise web.HTTPBadRequest(
                    text="Unmatched closing parenthesis in query parameter 'embed' at '%s'" % rest
                )
            if len(seen) == 1:
                result[sub_query_info[0]] = embed[sub_query_info[1]:pos]
        else:
            if token in seen[0]:
                message = "Link relation '%s' mentioned more than once in query parameter 'embed' at '%s'"
                raise web.HTTPBadRequest(
                    text=message % (token, rest)
                )
            if token in ('self',):
                message = "Link relation '%s' can not be embedded"
                raise web.HTTPBadRequest(
                    text= message % token
                )
            if len(seen) > MAX_QUERY_DEPTH:
                raise web.HTTPBadRequest(
                    text="Maximum query depth %i exceeded in query parameter 'embed' at '%s'" % (MAX_QUERY_DEPTH, rest)
                )
            seen[0].add(token)
            current = token
            if len(seen) == 1:
                result[token] = None
    if len(seen) > 1:
        raise web.HTTPBadRequest(
            text="Unmatched opening parenthesis in query parameter 'embed' at position %d" % sub_query_info[1]
        )
    return result
