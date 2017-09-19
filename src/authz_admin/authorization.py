import logging
import re
import typing as T

from aiohttp import web
import jwt

_logger = logging.getLogger(__name__)


async def _extract_scopes(request: web.Request,
                          _security_scheme: T.Dict) -> T.Set:
    authorization_header = request.headers.get('authorization')
    if authorization_header is None:
        return set()
    match = re.fullmatch(r'Bearer ([-\w]+=*\.[-\w]+=*\.[-\w]+=*)', authorization_header)
    if not match:
        return set()
    try:
        access_token = jwt.decode(
            match[1], verify=True,
            key=request.app['config']['authz_admin']['access_secret'],
            algorithms=['HS256']
        )
    except jwt.InvalidTokenError as e:
        raise web.HTTPBadRequest(text='Invalid Bearer token') from None
    if 'scopes' not in access_token or not isinstance(access_token['scopes'], list):
        raise web.HTTPBadRequest(
            text='No scopes in access token'
        )
    return set(access_token['scopes'])


async def _extract_api_key_info(request: web.Request,
                                security_scheme: T.Dict) -> T.Any:
    assert security_scheme['in'] == 'header'
    assert security_scheme['name'] == 'Authorization'
    authorization_header = request.headers.get('authorization')
    if authorization_header is None:
        return False
    match = re.fullmatch(r'apikey ([-\w]+=*)', authorization_header)
    if not match:
        return False
    return match[1] == request.app['config']['authz_admin']['api_key']


async def _extract_authz_info(request: web.Request,
                              security_definitions: T.Dict[str, T.Dict[str, T.Any]]):
    result = {}
    for key, security_scheme in security_definitions.items():
        security_type = security_scheme['type']
        if security_type == 'oauth2':
            result[key] = await _extract_scopes(request, security_scheme)
        elif security_type == 'apiKey':
            result[key] = await _extract_api_key_info(request, security_scheme)
        else:
            _logger.error('Unknown security type: %s' % security_type)
            raise web.HTTPInternalServerError()
    return result


async def middleware(app: web.Application, handler):
    async def middleware_handler(request: web.Request) -> web.Response:
        swagger = app['swagger']
        security_definitions = swagger.specification['securityDefinitions']
        request['authz_info'] = await _extract_authz_info(request, security_definitions)
        return await handler(request)
    return middleware_handler


async def enforce_one_of(request: web.Request,
                         security_requirements: T.List[T.Dict[str, T.Optional[T.Iterable]]]):
    for security_requirement in security_requirements:
        if await _enforce_all_of(request, security_requirement):
            return
    raise web.HTTPUnauthorized()


async def _enforce_all_of(request: web.Request,
                          security_requirements: T.Dict[str, T.Optional[T.Iterable]]) -> bool:
    swagger = request.app['swagger']
    security_definitions = swagger.specification['securityDefinitions']
    for requirement, scopes in security_requirements.items():
        authz_info = request['authz_info'][requirement]
        security_type = security_definitions[requirement]['type']
        if security_type == 'oauth2':
            if len(set(scopes) - authz_info) > 0:
                return False
        elif security_type == 'apiKey':
            if not authz_info:
                return False
        else:
            _logger.error('Unexpected security type: %s' % security_type)
            raise web.HTTPInternalServerError()
    return True
