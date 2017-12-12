import logging
import typing as T

from aiohttp import web
import jwt

_logger = logging.getLogger(__name__)


async def _enforce_basic(request: web.Request, securityDefinition):
    raise web.HTTPNotImplemented()


async def _enforce_apiKey(request: web.Request, securityDefinition):
    raise web.HTTPNotImplemented()


async def _enforce_oauth2(request: web.Request,
                          securityDefinition,
                          required_scopes: T.List[str]):
    authorization = request.headers.get('authorization')
    if authorization is None:
        return None
    access_token = jwt.decode(
        authorization, verify=True,
        key=request.app['config']['authz_admin']['access_secret'],
        algorithms=['hs256']
    )
    if 'scopes' not in access_token or not isinstance(access_token['scopes'], list):
        raise web.HTTPBadRequest(
            text='No scopes in access token'
        )
    scopes = set(access_token['scopes'])
    missing_scopes = set(required_scopes) - scopes
    if len(missing_scopes) > 0:
        raise web.HTTPUnauthorized(
            text="Missing scopes: %s" % missing_scopes
        )
    return scopes


async def _enforce_all_of(request: web.Request,
                          securityDefinitions: T.Dict[str, T.Any],
                          policies: T.Dict[str, T.List[str]]):
    result = {}
    for key, value in securityDefinitions.items():
        securityDefinition = securityDefinitions[key]
        securityType = securityDefinition['type']
        if securityType == 'oauth2':
            authz_info = await _enforce_oauth2(request, securityDefinition, value)
        elif securityType == 'apiKey':
            authz_info = await _enforce_apiKey(request, securityDefinition)
        elif securityType == 'basic':
            authz_info = await _enforce_basic(request, securityDefinition)
        else:
            authz_info = None
        if authz_info is None:
            raise web.HTTPInternalServerError()
        result[key] = authz_info
    return result


async def _enforce_one_of(request: web.Request, security_definitions: T.Dict[str, T.Any], security: T.List):
    for policy in security:
        authz_info = _enforce_all_of(request, security_definitions, policy)
        if authz_info is not None:
            request['authz_info'] = authz_info
            return
    raise web.HTTPUnauthorized()


# noinspection PyUnusedLocal
async def authorization(app: web.Application, handler):
    async def middleware_handler(request: web.Request) -> web.Response:
        swagger = request.app['swagger']
        base_path = swagger.base_path
        paths = swagger.specification['paths']
        path, _ = swagger.get_path_spec(
            request.raw_path
        )
        if path is None:
            raise web.HTTPNotFound(
                text="Path '%s' is not in the openapi definition." % request.path
            )
        assert path.startswith(base_path)
        path = path[len(base_path):]
        method = request.method.lower()
        if method == 'head':
            method = 'get'
        if method not in paths[path]:
            await handler(request)  # This should raise HTTPMethodNotAllowed
            _logger.warning('Unexpected code path.')
            raise web.HTTPMethodNotAllowed(request.method, paths[path].keys())
        method_info = paths[path][method]
        if 'security' in method_info:
            securityDefinitions = swagger.specification['securityDefinitions']
            _enforce_one_of(request,
                            securityDefinitions,
                            method_info['security'])
        return await handler(request)
    return middleware_handler
