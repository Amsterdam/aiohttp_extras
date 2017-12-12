import collections.abc
import inspect
import logging
import re
import typing as T

from aiohttp import web

from ._parse_embed import *
from ... import (
    _json,
    _view
)

_logger = logging.getLogger(__name__)


async def _hal_json_serializer(view) -> collections.AsyncIterable:
    # language=rst
    """

    Todo:
        Documentation?

    """
    assert isinstance(view, _view.View), "Parameter 'view' must have type _view.View."
    assert isinstance(view, HALJSONMixin)
    return _json.encode(await view.to_dict())


class HALJSONMixin(object):
    # language=rst
    """

    Todo:
        Documentation

    """

    def __init_subclass__(cls):
        """



        This is *implicitly* a class method. See
        :python:meth:`object.__init_subclass` for details.

        """
        super().__init_subclass__()
        assert isinstance(cls, _view.View)
        cls.add_serializer('application/hal+json; charset=utf-8', _hal_json_serializer)
        cls.add_serializer('application/json; charset=utf-8', _hal_json_serializer)

    def add_embed_to_url(self, url: web.URL, link_relation):
        embed = self.embed.get(link_relation)
        if embed is None:
            return url
        return url.update_query(embed=embed)

    @property
    def embed(self):
        if self.__embed is None:
            embed = ','.join(self.query.getall('embed', default=''))
            self.__embed = parse_embed(embed)
        return self.__embed

    async def to_dict(self):
        # language=rst
        """

        Todo:
            Implementation. This method is not yet finished.

        """
        result = await self.attributes()
        if hasattr(self, 'etag'):
            etag = await self.etag()
            if isinstance(etag, str):
                result['_etag'] = etag
        result['_links'] = await self.links()
        if 'self' not in result['_links']:
            result['_links']['self'] = self.to_link
        result['_embedded'] = await self.embedded()
        if len(result['_embedded']) == 0:
            del result['_embedded']
        return result

    @property
    def link_title(self) -> T.Optional[str]:
        # language=rst
        """The title of this resource, to be used in link objects.

        Returns:
            The title of this resource, or ``None``, in which case the `title`
            attribute is omitted from the HAL link object.  See also
            :meth:`to_link`.

        Subclasses can override this default implementation.

        """
        return None

    @property
    def to_link(self) -> T.Dict[str, str]:
        """The HAL JSON link object to this resource."""
        result = {'href': str(self.canonical_rel_url)}
        if self.link_name is not None:
            result['name'] = self.link_name
        if self.link_title is not None:
            result['title'] = self.link_title
        return result

    @property
    def link_name(self) -> T.Optional[str]:
        # language=rst
        """A more or less unique name for the resource.

        This default implementation returns the last path segment of the url of
        this resource if that last path segment is templated.  Otherwise `None`
        is returned (in which case there's no `name` attribute in link objects
        for this resource).  See also :meth:`to_link`.

        Subclasses can override this default implementation.

        """
        formatter = self.aiohttp_resource().get_info().get('formatter')
        if formatter is not None and re.search(r'\}[^/]*/?$', formatter):
            return self.rel_url.name or self.rel_url.parent.name
        return None

    async def attributes(self):
        # language=rst
        """

        This default implementation returns *no* attributes, ie. an empty
        `dict`.

        Most subclasses should override this default implementation.

        """
        return {}

    async def _links(self) -> T.Dict[str, T.Any]:
        # language=rst
        """

        Called by :meth:`.links` and :meth:`.embedded`.  See the
        documentation of these methods for more info.

        Most subclasses should override this default implementation.

        :returns: This method must return a dict.  The values must have one of
            the following types:

            -   asynchronous generator of `.View` objects
            -   generator of `.View` objects
            -   a `.View` object
            -   a *link object*
            -   Iterable of `.View`\s and/or *link objects* (may be mixed)

            where *link object* means a HALJSON link object, ie. a `dict` with
            at least a key ``href``.

        """
        return {}

    async def embedded(self) -> T.Dict[str, T.Any]:
        result = {}
        _links = await self._links()
        for key, value in _links.items():
            if key in self.embed:
                if (
                    inspect.isasyncgen(value) or
                    inspect.isgenerator(value) or
                    isinstance(value, _view.View) or
                    isinstance(value, collections.abc.Iterable)
                ):
                    result[key] = value
                else:
                    _logger.error("Don't know how to embed object: %s", value)
        return result

    async def links(self) -> T.Dict[str, T.Any]:
        result = {}
        _links = await self._links()
        for key, value in _links.items():
            if key == 'item':
                key = 'item'
            if isinstance(value, _view.View):
                if key not in self.embed:
                    result[key] = value.to_link
            elif inspect.isasyncgen(value):
                if key not in self.embed:
                    async def g1(resources):
                        async for resource in resources:
                            yield resource.to_link
                    result[key] = g1(value)
            elif inspect.isgenerator(value):
                if key not in self.embed:
                    def g2(resources):
                        for resource in resources:
                            yield resource.to_link
                    result[key] = g2(value)
            elif isinstance(value, collections.Mapping):
                if key in self.embed:
                    _logger.info('Client asked to embed unembeddable object: %s', value)
                result[key] = value
            elif isinstance(value, collections.abc.Iterable):
                def g3(p_key, p_value):
                    for o in p_value:
                        if not isinstance(o, _view.View):
                            if p_key in self.embed:
                                _logger.info('Client asked to embed unembeddable object: %s', o)
                            yield o
                        elif p_key not in self.embed:
                            yield o.to_link
                result[key] = g3(key, value)
            elif key not in self.embed:
                _logger.error("Don't know how to render object as link: %s", value)
        return result
