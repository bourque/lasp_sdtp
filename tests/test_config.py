"""Tests for ``config.py``

Authors
-------
    Matthew Bourque

Use
---
    pytest test_config.py
"""

from lasp_sdtp.config import get_admin_config
from lasp_sdtp.config import get_subscriber_config


def test_get_admin_config():
    """Tests the ``get_admin_config`` function"""

    config = get_admin_config()

    required_keys = [
        'email_address',
        'email_password',
        'filesystem_loc',
        'subscriber_queues_loc']

    for key in required_keys:
        assert key in config


def test_get_subscriber_config():
    """Tests the ``get_subscriber_config`` function"""

    config = get_subscriber_config()

    required_keys = [
        'account_expiration_period',
        'checksum_type',
        'connection_string',
        'endpoint',
        'expiration_period',
        'max_num_files',
        'num_download_threads',
        'username']

    for key in required_keys:
        assert key in config
