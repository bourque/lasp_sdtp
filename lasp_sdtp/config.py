"""Code to support admin- and subscriber-specific configurations.

Gathers configuration details from the ``admin_config.json`` and
``subscriber_config.json`` files and makes the data available via importable
variables.

This module also contains a SubscriberConfig class which a subscriber may use
to create and validate a ``subscriber_config.json`` file.

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

# TODO: Implement more complex jsonschema for checking nested objects

import json
import jsonschema
from pathlib import Path


def _get_admin_config() -> dict:
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


def _get_subscriber_config() -> dict:
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
admin_config = _get_admin_config()
subscriber_config = _get_subscriber_config()


class SubscriberConfig():
    """Class for storing subscriber configuration data.  Contains methods to
    validate and save the configuration.

    Attributes
    ----------
    account_expiration_period : int
        The number of days before the account expires.  Must be ``1`` or
        greater.
    checksum_type : str
        The checksum type.  Currently, only sha256 is supported.
    distinguished_name : str
        The distinguished name used for authentication
    expiration_period : int
        The number of days before a file expires in the file queue.  Must be
        ``1`` or greater.
    max_num_files : int
        The maximum number of files to return in a file list.
    num_download_threads : int
        The number of parallel threads to use for file transfers.
    username : str
        The username for the account.
    streams : dict
        A dictionary defining the streams (and their specific tags and extras)
        to use.

    Methods
    -------
    validate(config)
        Validate the configuration.
    save()
        Save the configuration to the ``subscriber_config.json`` file.
    """

    def __init__(self):

        self.account_expiration_period = 1800
        self.checksum_type = 'sha256'
        self.distinguished_name = ''
        self.expiration_period = 180
        self.max_num_files = 10000
        self.num_download_threads = 5
        self.username = ''
        self.streams = None

    def validate(self, config):
        """Validate the configuration.

        Parameters
        ----------
        config : dict
            The configuration to validate

        Raises
        ------
        jsonschema.ValidationError
            Raised if the config is not valid
        """

        print('Checking to see if config is valid')

        # Define the expected schema
        schema = {
            "type": "object",  # Must be a JSON object
            "properties": {  # List of all possible entries and their tyoes
                "account_expiration_period": {"type": "integer", "minimum": 1},
                "checksum_type": {"type": "string", "enum": ["sha256"]},
                "distinguished_name": {"type": "string"},
                "expiration_period": {"type": "integer", "minimum": 1},
                "max_num_files": {"type": "integer", "minimum": 1, "maximum": 10000},
                "num_download_threads": {"type": "integer", "minimum": 1},
                "username": {"type": "string", "minLength": 5, "maxLength": 30},
                "streams": {"type": "object"}
            },
            "required": ["account_expiration_period"]
        }

        # Validate the (high-level) config
        jsonschema.validate(instance=config, schema=schema)

        stream_schema = {
            "type": "object",
            "patternProperties": {
                ".*": {"type": "object"}  # Any string
            }
        }

        # Validate the streams config
        jsonschema.validate(instance=config['streams'], schema=stream_schema)

        # If no exception occurred, schema is valid
        print('Configuration is valid.')

    def save(self):
        """Save the configuration to the ``subscriber_config.json`` file"""

        filename = 'subscriber_config.json'

        # Convert the configuration to a dictionary
        config = self.__dict__

        # Check to see if the configuration is valid before saving
        self.validate(config)

        # Give user a chance to avoid overwrite
        save_file = False
        if Path(filename).exists:
            response = input('Are you sure you want to overwrite? (y/n)\n')
            if response == 'y':
                save_file = True
            elif response == 'n':
                pass
            else:
                print('response not recognized')
        else:
            save_file = True

        # Save the file
        if save_file:
            with open(filename, 'w') as f:
                json.dump(config, f, indent=4)
            print('\nConfiguration file saved to filename')
