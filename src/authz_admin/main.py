import asyncio
import logging
import math
import os.path
import sys
import time

import jwt
import swagger_parser
import uvloop
from aiohttp import web

import rest_utils
from . import handlers, database, config, authorization

_logger = logging.getLogger(__name__)


def access_token(scope: str, secret) -> bytes:
    return jwt.encode({
        'sub': 'dp:datapunt@amsterdam.nl',
        'iat': math.floor(time.time()) - 5,
        'exp': math.floor(time.time()) + 3600 * 12,
        'scope': scope
    }, secret)


def add_routes(app: web.Application):
    base_path = app['swagger'].base_path
    app.router.add_static(base_path + '/swagger-ui', 'swagger-ui/dist', follow_symlinks=True)
    app.router.add_route('GET', base_path + '/authorization', handlers.authorization, name='authorization')
    handlers.Root.add_to_router(app.router, base_path + '/')
    handlers.Accounts.add_to_router(app.router, base_path + '/accounts')
    handlers.Account.add_to_router(app.router, base_path + '/accounts/{account}')
    handlers.Datasets.add_to_router(app.router, base_path + '/datasets')
    handlers.Dataset.add_to_router(app.router, base_path + '/datasets/{dataset}')
    handlers.Scope.add_to_router(app.router, base_path + '/datasets/{dataset}/{scope}')
    handlers.Profiles.add_to_router(app.router, base_path + '/profiles')
    handlers.Profile.add_to_router(app.router, base_path + '/profiles/{profile}')
    handlers.Roles.add_to_router(app.router, base_path + '/roles')
    handlers.Role.add_to_router(app.router, base_path + '/roles/{role}')


# noinspection PyUnusedLocal
async def on_response_prepare(request: web.Request, response: web.Response):
    response.headers.add('Access-Control-Allow-Origin', '*')


def build_application(loop=None):
    # language=rst
    """The entry point of the authorization administration service.

    :returns int: the exit status of the process. See
        also the ``console_scripts`` in :file:`setup.py`.

    """

    # Build the application
    app = web.Application(
        middlewares=[
            rest_utils.middleware,
            web.normalize_path_middleware(),
            authorization.middleware
        ],
        loop=loop
    )
    app['config'] = config.load()
    app['etag'] = rest_utils.ETagGenerator().update(app['config']['authz_admin']).etag()
    swagger_path = os.path.join(os.path.dirname(__file__), 'openapi.yml')
    _logger.info("Loading swagger file '%s'", swagger_path)
    app['swagger'] = swagger_parser.SwaggerParser(
        swagger_path=swagger_path
    )
    app['metadata'] = database.metadata()
    add_routes(app)
    app.on_response_prepare.append(on_response_prepare)
    app.on_startup.append(database.initialize_app)
    return app


def main():
    # language=rst
    """The entry point of the authorization administration service.

    :returns int: the exit status of the process. See
        also the ``console_scripts`` in :file:`setup.py`.

    """
    # Set UVLoop as our default event loop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    app = build_application()
    SERVICE_CONFIG = app['config']['authz_admin']
    web.run_app(
        app,
        port=SERVICE_CONFIG['bind_port']
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
