"""Tests for the ``config.py`` module.

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_config.py
"""

import pytest

from lasp_sdtp.config import SubscriberConfig
from lasp_sdtp.config import _get_admin_config
from lasp_sdtp.config import _get_subscriber_config

config = SubscriberConfig()


def test_get_admin_config():
    """Tests the ``get_admin_config`` function"""

    required_keys = {
        'db_connection_string': str,
        'email_address': str,
        'email_password': str,
        'email_port': int,
        'email_server': str,
        'endpoint': str,
        'filesystem_loc': str,
        'data_cache_loc': str
    }

    # Get the config data
    config = _get_admin_config()
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
        'distinguished_name': str,
        'expiration_period': int,
        'max_num_files': int,
        'num_download_threads': int,
        'username': str,
        'streams': dict
    }

    # Get the config data
    config = _get_subscriber_config()
    for key in required_keys:

        # Check that the file has the required key
        assert key in config

        # Check that the value is of expected type
        assert isinstance(config[key], required_keys[key])

    # Check that the checksum type is supported
    assert config['checksum_type'] in ['sha256']


def test_validate_valid_config():
    """Test the ``validate`` method with a valid config"""

    # Create a valid config instance to test with
    valid_config = SubscriberConfig()
    valid_config.username = 'admin'
    valid_config.distinguished_name = 'some_string'
    valid_config.streams = {}

    # Try to validate the config
    config.validate(valid_config.__dict__)


def test_validate_invalid_configs():
    """Test the ``validate`` method with an invalid config"""

    # Create an invalid config instances to test with
    invalid_config = SubscriberConfig()
    invalid_config.username = 'a'  # invalid username

    # Try to validate the config
    with pytest.raises(Exception) as error:
        config.validate(invalid_config.__dict__)
    assert 'ValidationError' in str(error)
