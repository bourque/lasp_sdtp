"""Gathers configuration details for configuration JSON files and makes the
data available via importable variables

Authors
-------
    Matthew Bourque

Use
---
    The config variables within this module are inteneded to be imported and
    used from other modules, e.g.:
    ::
        from lasp_sdtp.config import susbsriber_config
"""

import json
import os


def get_admin_config():
    """Return admin configuration details

    Returns
    -------
    config : dict
        A dictionary containing configuration details
    """

    config_file_location = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin_config.json')
    with open(config_file_location, 'r') as f:
        config = json.load(f)

    return config


def get_subscriber_config():
    """Return subscriber configuration details

    Returns
    -------
    config : dict
        A dictionary containing configuration details
    """

    config_file_location = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'subscriber_config.json')
    with open(config_file_location, 'r') as f:
        config = json.load(f)

    return config


admin_config = get_admin_config()
subscriber_config = get_subscriber_config()
