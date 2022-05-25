"""Tests for the ``config.py`` module

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_config.py
"""

from lasp_sdtp.config import get_admin_config
from lasp_sdtp.config import get_subscriber_config


def test_get_admin_config():
    """Tests the ``get_admin_config`` function"""

    required_keys = {
        'db_connection_string': str,
        'email_address': str,
        'email_password': str,
        'endpoint': str,
        'filesystem_loc': str,
        'subscriber_queues_loc': str
    }

    # Get the config data
    config = get_admin_config()
    for key in required_keys:

        # Check that the file has the required key
        assert key in config

        # Check that the value is of expected type
        assert isinstance(config[key], required_keys[key])


def test_get_subscriber_config():
    """Tests the ``get_subscriber_config`` function"""

    required_keys = {
        'account_expiration_period': int,
        'checksum_type': str,
        'expiration_period': int,
        'max_num_files': int,
        'num_download_threads': int,
        'username': str
    }

    # Get the config data
    config = get_subscriber_config()
    for key in required_keys:

        # Check that the file has the required key
        assert key in config

        # Check that the value is of expected type
        assert isinstance(config[key], required_keys[key])

    # Check that the checksum type is supported
    assert config['checksum_type'] in ['sha256']
