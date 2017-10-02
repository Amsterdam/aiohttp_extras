import abc
import logging
import typing as T

from aiohttp import web

import rest_utils
from . import authorization

_logger = logging.getLogger(__name__)


class OAuth2View(rest_utils.View, metaclass=abc.ABCMeta):
    """Default Query Parameters Mixin."""

    @property
    def default_query_params(self: rest_utils.View) -> T.Dict[str, str]:
        # language=rst
        """

        See :func:`rest_utils.View.default_query_params`.

        """
        method = self.request.method.lower()
        if method == 'head':
            method = 'get'
        path, path_info = self.request.app['swagger'].get_path_spec(
            self.rel_url.raw_path,
            action=method
        )
        if path is None:
            _logger.error("Couldn't find swagger info for path %s", str(self.rel_url))
            return {}
        return dict({
            param: param_info['default']
            for param, param_info in path_info.get('parameters', {}).items()
            if 'default' in param_info
        })

    @property
    @abc.abstractmethod
    def link_title(self) -> str:
        pass

    @property
    def to_link(self):
        result = super().to_link
        result['title'] = self.link_title
        return result

    async def options(self):
        # language=rst
        """Dummy implementation.

        .. todo:: Fetch the actual allowed methods from the swagger definition,
            and return all the operation items for this path in the body.

        """

        return web.Response(
            text='GET,HEAD,OPTIONS,PATCH,POST,PUT',
            status=200,
            headers={
                'Allow': 'GET,HEAD,OPTIONS,PATCH,POST,PUT'
            }
        )

    async def to_dict(self):
        swagger = self.request.app['swagger']
        base_path = swagger.base_path
        paths = swagger.specification['paths']
        path, _ = swagger.get_path_spec(
            self.rel_url.raw_path
        )
        assert path is not None
        assert path.startswith(base_path)
        path = path[len(base_path):]
        if 'get' not in paths[path]:
            raise web.HTTPMethodNotAllowed(
                'GET', list([
                    method.upper() for method in paths[path].keys()
                ])
            )
        method_info = paths[path]['get']
        if 'security' in method_info:
            await authorization.enforce_one_of(self.request, method_info['security'])
        return await super().to_dict()
