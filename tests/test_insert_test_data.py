"""Tests for ``insert_test_data.py``

Authors
-------
    Matthew Bourque

Use
---
    pytest test_insert_test_data.py
"""

from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.insert_test_data import _get_checksum


def test_get_checksum():
    """Tests the ``_get_checksum`` function"""

    checksum = _get_checksum()

    # Check that the checksum type is correct
    assert checksum.split(':')[0] == subscriber_config['checksum_type']

    # Check that the checsum is of proper length
    assert len(checksum.split(':')[-1]) == 64
