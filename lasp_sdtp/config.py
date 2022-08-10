"""Gathers configuration details from the ``admin_config.json`` and
``subscriber_config.json`` files and makes the data available via importable
variables.

Authors
-------
    Matthew Bourque

Use
---
    The config variables within this module are intended to be imported and
    used from other modules, i.e.:
    ::
        from lasp_sdtp.config import admin_config
        from lasp_sdtp.config import subscriber_config
"""

import json
from pathlib import Path


def get_admin_config() -> dict:
    """Return admin configuration data.

    Returns
    -------
    config : dict
        A dictionary containing the configuration details
    """

    config_file_location = Path(__file__).parents[1] / 'data' / 'admin_config.json'
    with open(config_file_location, 'r') as f:
        config = json.load(f)

    # Prepend necessary directory to filesystem and subscriber queues
    config['filesystem_loc'] = str(Path.home() / config['filesystem_loc'])
    config['data_cache_loc'] = str(Path.home() / config['data_cache_loc'])

    return config


def get_subscriber_config() -> dict:
    """Return subscriber configuration data.

    Returns
    -------
    config : dict
        A dictionary containing the configuration details
    """

    config_file_location = Path(__file__).parents[1] / 'data' / 'subscriber_config.json'
    with open(config_file_location, 'r') as f:
        config = json.load(f)

    return config


# Make the config data global, so it can easily be imported
admin_config = get_admin_config()
subscriber_config = get_subscriber_config()
