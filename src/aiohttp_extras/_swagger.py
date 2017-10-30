import typing as T
import os

from aiohttp import web
from swagger_parser import swagger_parser

_SWAGGER_SYMBOL = 'aiohttp_extras.swagger_definition'


def swaggerize(app: web.Application, swagger_path: os.PathLike):
    app[_SWAGGER_SYMBOL] = swagger_parser
