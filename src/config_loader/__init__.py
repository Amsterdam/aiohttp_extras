"""
Module that loads configuration settings from a yaml file.

**Features**

- Environment interpolation with defaults
- JSON schema validation

**Example usage**::

    import config_loader
    import logging

    CONFIG = config_loader.load(
        path_to_config_file,
        path_to_config_schema_file
    )
    logging.config.dictConfig(CONFIG['logging'])

This module comes with an example JSON schema file :file:`schema_example.json`
that contains a schema definition for a dict that can be passed into
`logging.config.dictConfig`.

"""

from ._config_loader import *
