"""Gathers configuration details from the ``admin_config`` and ``subscriber_config``
JSON files and makes the data available via importable variables

Authors
-------
    Matthew Bourque

Use
---
    The config variables within this module are inteneded to be imported and
    used from other modules, i.e.:
    ::
        from lasp_sdtp.config import admin_config
        from lasp_sdtp.config import susbsriber_config
"""

import json
import os

HOME_DIR = os.path.expanduser('~')


def get_admin_config():
    """Return admin configuration data

    Returns
    -------
    config : dict
        A dictionary containing the configuration details
    """

    config_file_location = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin_config.json')
    with open(config_file_location, 'r') as f:
        config = json.load(f)

    # Prepend necessary directory to filesystem and subscriber queues
    config['filesystem_loc'] = os.path.join(HOME_DIR, config['filesystem_loc'])
    config['subscriber_queues_loc'] = os.path.join(HOME_DIR, config['subscriber_queues_loc'])

    return config


def get_subscriber_config():
    """Return subscriber configuration details

    Returns
    -------
    config : dict
        A dictionary containing the configuration details
    """

    config_file_location = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'subscriber_config.json')
    with open(config_file_location, 'r') as f:
        config = json.load(f)

    return config


# Make the config data global so it can easily be imported
admin_config = get_admin_config()
subscriber_config = get_subscriber_config()
