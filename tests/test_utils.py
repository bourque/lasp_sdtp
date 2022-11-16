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

# TODO: Add test for parse_api_response (requires mock request)
# TODO: Add test for parse_request_parameters (requires mock request)
# TODO: Add test for register_admin (requires database manipulation)

import datetime
import pytest

from lasp_sdtp.config import subscriber_config
from lasp_sdtp.utils import utils


TEST_TAGS = [
    ({'date': '19840404', 'start_date': None, 'end_date': None, 'maxfile': 10000, 'startfileid': 1}, False),
    ({'date': '1984-04-04', 'start_date': '1984-04-05', 'end_date': None, 'maxfile': 10000, 'startfileid': 1}, False),
    ({'date': '1984-04-04', 'start_date': None, 'end_date': '1984-04-05', 'maxfile': 10000, 'startfileid': 1}, False),
    ({'date': None, 'start_date': None, 'end_date': None, 'maxfile': 9999999999, 'startfileid': 1}, False),
    ({'date': '19840404', 'start_date': None, 'end_date': None, 'maxfile': 10000, 'startfileid': 'foo'}, False),
    ({'date': None, 'start_date': None, 'end_date': None, 'maxfile': 10000, 'startfileid': 1}, True),
    ({'date': '1984-04-04', 'start_date': None, 'end_date': None, 'maxfile': 10000, 'startfileid': 1}, True),
    ({'date': None, 'start_date': '1984-04-04', 'end_date': '1984-04-05', 'maxfile': 10000, 'startfileid': 1}, True)
]


def test_combine_metadata():
    """Tests the ``combine_metadata`` function"""

    filelist = [
        {'fileid': 1,
         'expires': datetime.datetime(2022, 9, 21, 0, 0),
         'shortname': 'TEST_FILE',
         'date': datetime.datetime(2022, 1, 1, 0, 0),
         'size': 1.0,
         'name': 'test_combine_metadata.txt',
         'checksum': 'foo',
         'stream': 'prod',
         'version': '01',
         'ingest_date': datetime.datetime(2022, 9, 20, 0, 0),
         'available': True,
         'deletion_date': None}
    ]

    tags_and_extras = [[
        {'fileid': 1, 'field_name': 'irradiance', 'field_type': 'tag', 'value': 'some_value'},
        {'fileid': 1, 'field_name': 'type', 'field_type': 'extra', 'value': 'some_value'}
    ]]

    expected_result = [{
        'fileid': 1,
        'data_product_id': 'tsis2',
        'expires': datetime.datetime(2022, 9, 21, 0, 0),
        'date': datetime.datetime(2022, 1, 1, 0, 0),
        'size': 1.0,
        'name': 'test_combine_metadata.txt',
        'checksum': 'foo',
        'ingest_date': datetime.datetime(2022, 9, 20, 0, 0),
        'available': True,
        'deletion_date': None,
        'tags': {
            'shortname': 'TEST_FILE',
            'stream': 'prod',
            'version': '01',
            'irradiance': 'some_value'
        },
        'extras': {
            'type': 'some_value'
        }
    }]

    result = utils.combine_metadata(filelist, tags_and_extras)

    assert result == expected_result


def test_get_checksum():
    """Tests the ``get_checksum`` function"""

    checksum = utils.get_checksum()

    # Check that the checksum type is correct
    assert checksum.split(':')[0] == subscriber_config['checksum_type']

    # Check that the checksum is of proper length
    assert len(checksum.split(':')[-1]) == 64


def test_get_shortname():
    """Tests the ``get_shortname`` function"""

    assert utils.get_shortname('tsis2_L1') == 'TSIS2_L1'


def test_validate_access():
    """Tests the ``validate_access`` function"""

    assert utils.validate_access(12345) is True  # This is a tsis2 data product which the 'ges_disc' user has access to
    assert utils.validate_access(23456) is False  # This is a 'restricted' data product


@pytest.mark.parametrize('fileid, expected_result', [(1, True), (-1, False), ('foo', False), (9999999999999999, False)])
def test_validate_fileid(fileid: int, expected_result: bool):
    """Tests the ``parse_api_response`` function"""

    assert utils.validate_fileid(fileid) == expected_result


@pytest.mark.parametrize('fileid_start, fileid_end, expected_result', [(1, 5, True), (5, 1, False), ('foo', 'bar', False), (-1, 5, False), (1, 9999999999999999, False)])
def test_validate_fileid_range(fileid_start: int, fileid_end: int, expected_result: bool):
    """Tests the ``parse_api_response`` function"""

    assert utils.validate_fileid_range(fileid_start, fileid_end) == expected_result


@pytest.mark.parametrize('tags, expected_result', TEST_TAGS)
def test_validate_tags(tags, expected_result):
    """Tests the ``validate_tags`` function"""

    assert utils.validate_tags(tags) == expected_result
