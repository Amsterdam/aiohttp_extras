import collections.abc
import inspect
import logging
import re
import typing as T

from aiohttp import web
from multidict import MultiDict

from . import _json
from ._middleware import BEST_CONTENT_TYPE, ASSERT_PRECONDITIONS
from ._parse_embed import parse_embed
from ._etags import assert_preconditions

_logger = logging.getLogger(__name__)


def _slashify(s):
    assert isinstance(s, str)
    return s if s.endswith('/') else s + '/'


class View(web.View):

    SEGMENT_RE = re.compile(r'([^/{}]+)/?$')
    PATHS = {}
    PATTERNS = {}

    def __init__(
            self, request: web.Request,
            match_dict: T.Optional[collections.abc.Mapping]=None,
            embed=None
    ):
        super().__init__(request)
        if match_dict is None:
            rel_url = request.rel_url
        else:
            rel_url = self.aiohttp_resource().url_for(**match_dict)
        if embed is not None:
            rel_url = rel_url.update_query(embed=embed)
        self.__rel_url = rel_url
        self.__embed = None
        self.__query = None
        self.__canonical_rel_url = None
        self.__etag = None
        self.__match_dict = dict(
            # Ugly: we're using non-public member ``_match()`` of
            # :class:`aiohttp.web.Resource`.  But most alternatives are
            # equally ugly.
            self.aiohttp_resource()._match(self.rel_url.raw_path)
        )

    def __getitem__(self, item):
        # language=rst
        """Shorthand for ``self.match_dict[item]``"""
        return self.__match_dict[item]

    @property
    def match_dict(self):
        return self.__match_dict

    def add_embed_to_url(self, url: web.URL, link_relation):
        embed = self.embed.get(link_relation)
        if embed is None:
            return url
        return url.update_query(embed=embed)

    @property
    def rel_url(self) -> web.URL:
        # language=rst
        """The relative URL as passed to the constructor."""
        return self.__rel_url

    @property
    def canonical_rel_url(self) -> web.URL:
        # language=rst
        """Like :meth:`rel_url`, but with all default query parameters explicitly listed."""
        if self.__canonical_rel_url is None:
            self.__canonical_rel_url = self.__rel_url.with_query(self.query)
        # noinspection PyTypeChecker
        return self.__canonical_rel_url

    @property
    def to_link(self) -> T.Dict[str, str]:
        """The HAL JSON link object to this resource."""
        result = {'href': str(self.canonical_rel_url)}
        if self.link_name is not None:
            result['name'] = self.link_name
        if self.link_title is not None:
            result['title'] = self.link_title
        return result

    async def etag(self) -> T.Union[None, bool, str]:
        # language=rst
        """

        Return values have the following meanings:

        ``True``
            Resource exists but doesn't support ETags
        ``False``
            Resource doesn't exist and doesn't support ETags
        ``None``
            Resource doesn't exist and supports ETags.
        ETag string:
            Resource exists and supports ETags.

        """
        return isinstance(self.aiohttp_resource(), web.PlainResource)

    @property
    def query(self):
        # language=rst
        """Like ``self.rel_url.query``, but with default parameters added.

        These default parameters are retrieved from the swagger definition.

        """
        if self.__query is None:
            self.__query = MultiDict(self.default_query_params)
            self.__query.update(self.__rel_url.query)
        return self.__query

    @property
    def embed(self):
        if self.__embed is None:
            embed = ','.join(self.query.getall('embed', default=[]))
            self.__embed = parse_embed(embed)
        return self.__embed

    @staticmethod
    def construct_resource_for(request: web.Request, rel_url: web.URL) \
            -> T.Optional[web.View]:
        # language=rst
        """

        .. deprecated:: v0

            Only used by :meth:`PlainView._links` and
            :meth:`DynamicView._links`, which are themselves deprecated.

        """
        for resource in request.app.router.resources():
            match_dict = resource._match(rel_url.raw_path)
            if match_dict is not None:
                if hasattr(resource, 'rest_utils_class'):
                    return resource.rest_utils_class(request, rel_url)
                _logger.error("Path %s doesn't resolve to rest_utils.Resource.", str(rel_url))
                return None
        return None

    @property
    def default_query_params(self) -> T.Dict[str, str]:
        return {}

    @classmethod
    def add_to_router(cls,
                      router: web.UrlDispatcher,
                      path: str,
                      expect_handler: T.Callable=None):
        # language=rst
        """Adds this View class to the aiohttp router."""
        cls._aiohttp_resource = router.add_resource(path)
        # Register the current class in the appropriate registry:
        if isinstance(cls._aiohttp_resource, web.DynamicResource):
            View.PATTERNS[cls._aiohttp_resource.get_info()['pattern']] = cls
        elif isinstance(cls._aiohttp_resource, web.PlainResource):
            View.PATHS[cls._aiohttp_resource.get_info()['path']] = cls
        else:
            _logger.critical("aiohttp router method 'add_resource()' returned resource object of unexpected type %s", cls._aiohttp_resource.__class__)
        cls._aiohttp_resource.rest_utils_class = cls
        cls._aiohttp_resource.add_route('*', cls, expect_handler=expect_handler)
        return cls._aiohttp_resource

    @classmethod
    def aiohttp_resource(cls) -> T.Union[web.PlainResource, web.DynamicResource]:
        assert hasattr(cls, '_aiohttp_resource'), \
            "%s.aiohttp_resource() called before .add_to_router()" % cls
        return cls._aiohttp_resource

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

    @property
    def link_title(self) -> T.Optional[str]:
        # language=rst
        """The title of this resource, to be used in link objects.

        This default implementation returns `None`, and there's no `title`
        attribute in HAL link objects.  See also :meth:`to_link`.

        Subclasses can override this default implementation.

        """
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
                if (inspect.isasyncgen(value) or
                    inspect.isgenerator(value) or
                    isinstance(value, View) or
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
            if isinstance(value, View):
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
                def g3(key, value):
                    for o in value:
                        if not isinstance(o, View):
                            if key in self.embed:
                                _logger.info('Client asked to embed unembeddable object: %s', o)
                            yield o
                        elif key not in self.embed:
                            yield o.to_link
                result[key] = g3(key, value)
            elif key not in self.embed:
                _logger.error("Don't know how to render object as link: %s", value)
        return result

    async def get(self) -> web.StreamResponse:

        # Assert we're not calling `get()` recursively within a single request:
        assert 'GET_IN_PROGRESS' not in self.request
        self.request['GET_IN_PROGRESS'] = True

        etag = await self.etag()
        if not etag:
            raise web.HTTPNotFound()
        assert_preconditions(self.request, etag)
        if self.request.method == 'GET':
            data = await self.to_dict()
        response = web.StreamResponse()
        if isinstance(await self.etag(), str):
            response.headers.add('ETag', await self.etag())
        response.content_type = self.request[BEST_CONTENT_TYPE]
        response.enable_compression()
        if str(self.canonical_rel_url) != str(self.request.rel_url):
            response.headers.add('Content-Location', str(self.canonical_rel_url))
        await response.prepare(self.request)
        if self.request.method == 'GET':
            async for chunk in _json.json_encode(data):
                response.write(chunk)
        response.write_eof()
        del self.request['GET_IN_PROGRESS']
        return response

    async def head(self):
        return await self.get()

    async def to_dict(self):
        result = await self.attributes()
        if isinstance(await self.etag(), str):
            result['_etag'] = await self.etag()
        result['_links'] = await self.links()
        if 'self' not in result['_links']:
            result['_links']['self'] = self.to_link
        result['_embedded'] = await self.embedded()
        if len(result['_embedded']) == 0:
            del result['_embedded']
        return result
