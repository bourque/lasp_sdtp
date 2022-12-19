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
from lasp_sdtp.utils.properties import REQUIRED_ADMIN_CONFIG_KEYS
from lasp_sdtp.utils.properties import REQUIRED_SUBSCRIBER_CONFIG_KEYS

config = SubscriberConfig()


def test_get_admin_config():
    """Tests the ``get_admin_config`` function"""

    # Get the config data
    config = _get_admin_config()
    for key in REQUIRED_ADMIN_CONFIG_KEYS:

        # Check that the file has the required key
        assert key in config

        # Check that the value is of expected type
        assert isinstance(config[key], REQUIRED_ADMIN_CONFIG_KEYS[key])


def test_get_subscriber_config():
    """Tests the ``get_subscriber_config`` function"""

    # Get the config data
    config = _get_subscriber_config()
    for key in REQUIRED_SUBSCRIBER_CONFIG_KEYS:

        # Check that the file has the required key
        assert key in config

        # Check that the value is of expected type
        assert isinstance(config[key], REQUIRED_SUBSCRIBER_CONFIG_KEYS[key])

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
