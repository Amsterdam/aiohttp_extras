import collections.abc
import inspect
import logging
import re
import typing as T

from aiohttp import web
from multidict import MultiDict

from . import _json
from ._parse_embed import parse_embed
from ._etags import assert_preconditions

_logger = logging.getLogger(__name__)


def _slashify(s):
    assert isinstance(s, str)
    return s if s.endswith('/') else s + '/'


class HALJSONMixin(object):
    # language=rst
    """

    Todo:
        Documentation

    """

    async def to_dict(self):
        # language=rst
        """

        Todo:
            Implementation. This method is not yet finished.

        """
        result = await self.attributes()
        if hasattr(self, 'etag') and isinstance(await self.etag(), str):
            result['_etag'] = await self.etag()
        result['_links'] = await self.links()
        if 'self' not in result['_links']:
            result['_links']['self'] = self.to_link
        result['_embedded'] = await self.embedded()
        if len(result['_embedded']) == 0:
            del result['_embedded']
        return result

    async def attributes(self):
        # language=rst
        """

        This default implementation returns *no* attributes, ie. an empty
        `dict`.

        Most subclasses should override this default implementation.

        """
        return {}
