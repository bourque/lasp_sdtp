"""Tests for the ``utils.py`` module.

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_utils.py
"""

import pytest

from lasp_sdtp.config import subscriber_config
from lasp_sdtp.utils.utils import get_checksum
from lasp_sdtp.utils.utils import get_shortname
from lasp_sdtp.utils.utils import validate_fileid
from lasp_sdtp.utils.utils import validate_fileid_range


def test_get_checksum():
    """Tests the ``get_checksum`` function"""

    checksum = get_checksum()

    # Check that the checksum type is correct
    assert checksum.split(':')[0] == subscriber_config['checksum_type']

    # Check that the checksum is of proper length
    assert len(checksum.split(':')[-1]) == 64


def test_get_shortname():
    """Tests the ``get_shortname`` function"""

    assert get_shortname('tsis2_L1') == 'TSIS2_L1'


@pytest.mark.parametrize('fileid, expected_result', [(1, True), (-1, False), ('foo', False), (9999999999999999, False)])
def test_validate_fileid(fileid: int, expected_result: bool):
    """Tests the ``parse_api_response`` function"""

    assert validate_fileid(fileid) == expected_result


@pytest.mark.parametrize('fileid_start, fileid_end, expected_result', [(1, 5, True), (5, 1, False), ('foo', 'bar', False), (-1, 5, False), (1, 9999999999999999, False)])
def test_validate_fileid_range(fileid_start: int, fileid_end: int, expected_result: bool):
    """Tests the ``parse_api_response`` function"""

    assert validate_fileid_range(fileid_start, fileid_end) == expected_result
