#!/usr/bin/env python
"""See <https://setuptools.readthedocs.io/en/latest/>.
"""
from setuptools import setup, find_packages


setup(
    # Publication Metadata:
    version='0.1.3',
    name='datapunt_authz_admin',
    description="User Role Management Service",
    # long_description="",
    url='https://github.com/DatapuntAmsterdam/authz_admin',
    author='Amsterdam Datapunt',
    author_email='datapunt@amsterdam.nl',
    license='Mozilla Public License Version 2.0',
    classifiers=[
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
    ],


    # Entry points:
    entry_points={
        'console_scripts': [
            'authz_admin = authz_admin.main:main',
            # 'authn_service = oauth2.authn_service.main:main',
            # 'authz_service = oauth2.authz_service.main:start',
            # 'client_admin_service = oauth2.client_admin_service.server:start',
            # 'dummy_authz_service = oauth2.dummy_authz_service.main:main',
        ],
    },


    # Packages and Package Data:
    package_dir={'': 'src'},
    packages=find_packages('src'),
    package_data={
        'authz_admin': ['config_schema*.json', 'openapi*.json', 'openapi.yml']
    },


    # Requirements:
    # setup_requires=[
    #     'setuptools_git',
    #     # Nice if you like setuptools integration for PyTest:
    #     #'pytest-runner',
    # ],
    install_requires=[
        'aiodns', # Recommended by aiohttp docs
        'aiohttp',
        'aiohttp-jinja2',
        'aiopg',
        'cchardet', # Recommended by aiohttp docs
        'docutils',
        'jsonschema',
        'mimeparse',
        'PyYaml',
        'PyJWT',
        'SQLAlchemy',
        'swagger-parser',
        'uvloop', # Recommended by aiohttp docs
    ],
    extras_require={
        'docs': [
            'MacFSEvents',
            'Sphinx',
            'sphinx-autobuild',
            'sphinx-autodoc-typehints',
            'sphinx_rtd_theme',
        ],
        'test': [
            'alembic',
            'pytest',
            'pytest-cov',
            'pytest-aiohttp'
        ],
        'dev': [
            'aiohttp-devtools',
            'alembic',
            'jupyter',
        ]
    },
)
