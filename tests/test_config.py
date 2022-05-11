"""Tests for ``config.py``

Authors
-------
    Matthew Bourque

Use
---
    pytest test_config.py
"""

from lasp_sdtp.config import get_config


def test_get_config():
    """Tests the ``get_config`` function"""

    config = get_config()

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
