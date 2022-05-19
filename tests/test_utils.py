"""Tests for ``utils.py``

Authors
-------
    Matthew Bourque

Use
---
    pytest utils.py
"""

from lasp_sdtp.config import subscriber_config
from lasp_sdtp.utils.utils import get_checksum
from lasp_sdtp.utils.utils import get_shortname


def test_get_checksum():
    """Tests the ``get_checksum`` function"""

    checksum = get_checksum()

    # Check that the checksum type is correct
    assert checksum.split(':')[0] == subscriber_config['checksum_type']

    # Check that the checsum is of proper length
    assert len(checksum.split(':')[-1]) == 64


def test_get_shortname():
    """Tests the ``get_shortname`` function"""

    assert get_shortname('tsis2_L1') == 'TSIS2_L1'
