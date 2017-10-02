import logging

from aiohttp import web

_logger = logging.getLogger(__name__)


# ┏━━━━━━━━━━━━━━━━━━━━━┓
# ┃ Content Negotiation ┃
# ┗━━━━━━━━━━━━━━━━━━━━━┛

_AVAILABLE_CONTENT_TYPES = (
    "application/hal+json",
    "application/json",
)
_HAL_JSON_COMPATIBLE = {
    "application/hal+json",
    "application/*",
    "*/*"
}


def best_content_type(request: web.Request) -> str:
    # language=rst
    """The best matching Content-Type.

    Todo:
        Generalize. (Now, we only negotiate hal+json and friends.)

    Raises:
        aiohttp.web.HTTPNotAcceptable: if none of the available content types
            are acceptable by the client.  See :ref:`aiohttp web exceptions
            <aiohttp-web-exceptions>`.

    """
    if 'ACCEPT' not in request.headers:
        return "application/hal+json; charset=UTF-8"
    accept = ','.join(request.headers.getall('ACCEPT', ['*/*']))
    mime_types = [
        part.split(';', 2)[0].strip() for part in accept.split(',')
    ]
    if not _HAL_JSON_COMPATIBLE.isdisjoint(mime_types):
        return "application/hal+json; charset=UTF-8"
    elif "application/json" in mime_types:
        return "application/json; charset=UTF-8"
    else:
        body = ",".join(_AVAILABLE_CONTENT_TYPES).encode('ascii')
        raise web.HTTPNotAcceptable(
            body=body,
            content_type='text/plain; charset="US-ASCII"'
        )
