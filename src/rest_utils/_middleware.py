import logging

from aiohttp import web

from ._best_content_type import best_content_type
from ._etags import assert_preconditions

_logger = logging.getLogger(__name__)

BEST_CONTENT_TYPE = 'rest_utils.best_content_type'
ASSERT_PRECONDITIONS = 'rest_utils.assert_preconditions'
EMBED = 'rest_utils.embed'


# noinspection PyUnusedLocal
async def middleware(app: web.Application, handler):
    # language=rst
    """

    :param app:
    :param handler:
    :return:

    """
    async def middleware_handler(request: web.Request):
        request[BEST_CONTENT_TYPE] = best_content_type(request)
        return await handler(request)
    return middleware_handler
