"""
"""

import json
import os

def get_config():
    """Return configuration details

    Returns
    -------
    config : dict
        A dictionary containing configuration details
    """

    config_file_location = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    with open(config_file_location, 'r') as f:
        config = json.load(f)

    return config

config = get_config()