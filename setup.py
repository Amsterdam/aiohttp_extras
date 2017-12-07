#!/usr/bin/env python
"""See <https://setuptools.readthedocs.io/en/latest/>.
"""
from setuptools import setup, find_packages

tests_require = [
    'pytest',
    'pytest-cov',
    'pytest-aiohttp',
]

setup(


    # ┏━━━━━━━━━━━━━━━━━━━━━━┓
    # ┃ Publication Metadata ┃
    # ┗━━━━━━━━━━━━━━━━━━━━━━┛
    version='0.1.0',
    name='datapunt_aiohttp_extras',
    description="Stack for developing HTTP web services in Python",
    long_description="""
        This package integrates:

        -   HAL+JSON rendering of resources
        -   an asynchronous JSON encoder
        -   some extras for aiohttp (an asynchronous HTTP client and server) to
            facilitate building ReSTful services:

            -   ETags and conditional request handling
        -   OpenAPI definition parsing
        -   enforcing OpenAPI security requirements, including OAuth2
            authorization
        -   loading and validation of configuration data from multiple
            predefined paths

    """,
    url='https://github.com/Amsterdam/aiohttp_extras',
    author='Amsterdam City Data',
    author_email='datapunt@amsterdam.nl',
    license='Mozilla Public License Version 2.0',
    classifiers=[
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
    ],


    # ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    # ┃ Packages and package data ┃
    # ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
    package_dir={'': 'src'},
    packages=find_packages('src'),
    # package_data={
    #     'authz_admin': ['config_schema*.json', 'openapi.yml']
    # },


    # ┏━━━━━━━━━━━━━━┓
    # ┃ Requirements ┃
    # ┗━━━━━━━━━━━━━━┛
    python_requires='~=3.6',
    setup_requires=[
        'pytest-runner'
    ],
    install_requires=[
        'aiohttp',
        'PyYaml',
        'PyJWT',
        'swagger-parser',
    ],
    extras_require={
        'docs': [
            'MacFSEvents',
            'Sphinx',
            'sphinx-autobuild',
            'sphinx-autodoc-typehints',
            'sphinx-autodoc-napoleon-typehints',
            'sphinx_rtd_theme',
        ],
        'test': tests_require,
        'dev': [
            'aiohttp-devtools',

            # Recommended by aiohttp docs:
            'aiodns',   # optional asynchronous DNS client
            'cchardet', # optional fast character handling in C
            'uvloop',   # optional fast eventloop for asyncio
        ],
    },
    tests_require=tests_require,
)
