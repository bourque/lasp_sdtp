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

# TODO: Add test for filter_for_subscriber_tags (requires mock request)
# TODO: Add test for parse_api_response (requires mock request)
# TODO: Add test for parse_request_parameters (requires mock request)
# TODO: Add test for register_admin (requires database manipulation)

import datetime
from pathlib import Path
import pytest

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db
from lasp_sdtp.database.database_queries import query_for_account
from lasp_sdtp.utils import utils


TEST_TAGS = [
    ({'maxfile': 9999999999, 'startfileid': 1}, False),
    ({'maxfile': 10000, 'startfileid': 'foo'}, False),
    ({'maxfile': 10000, 'startfileid': 1}, True)
]

TEST_SHORTNAMES = [
    ('tsis2_L1_19840404.zip', 'TSIS2_L1'),
    ('tsis2_sim_cal_v01.zip', 'TSIS2_SIM_CAL'),
    ('tsis2_tim_cal_v01.zip', 'TSIS2_TIM_CAL'),
    ('tsis2_sim_L2_v01_19840404.zip', 'TSIS2_SIM_L2'),
    ('tsis2_tim_L2_v01_19840404.zip', 'TSIS2_TIM_L2'),
    ('tsis2_sc_L2_v01_19840404_19840405.zip', 'TSIS2_SC_L2'),
    ('tsis2_ssi_L3_c12h_v01_19840404_19840405.txt', 'TSIS2_SSI_L3_12HR_TXT'),
    ('tsis2_ssi_L3_c24h_v01_19840404_19840405.txt', 'TSIS2_SSI_L3_24HR_TXT'),
    ('tsis2_tsi_L3_c06h_v01_19840404_19840405.txt', 'TSIS2_TSI_L3_06HR_TXT'),
    ('tsis2_tsi_L3_c24h_v01_19840404_19840405.txt', 'TSIS2_TSI_L3_24HR_TXT'),
    ('tsis2_ssi_L3_c12h_v01_19840404_19840405.nc', 'TSIS2_SSI_L3_12HR_NC'),
    ('tsis2_ssi_L3_c24h_v01_19840404_19840405.nc', 'TSIS2_SSI_L3_24HR_NC'),
    ('tsis2_tsi_L3_c06h_v01_19840404_19840405.nc', 'TSIS2_TSI_L3_06HR_NC'),
    ('tsis2_tsi_L3_c24h_v01_19840404_19840405.nc', 'TSIS2_TSI_L3_24HR_NC')]


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
        {'fileid': 1, 'field_name': 'aperture', 'field_type': 'extra', 'value': 'some_value'}
    ]]

    expected_result = [{
        'fileid': 1,
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
            'aperture': 'some_value'
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


@pytest.mark.parametrize('shortname, expected_result', TEST_SHORTNAMES)
def test_get_shortname(shortname: str, expected_result: str):
    """Tests the ``get_shortname`` function"""

    assert utils.get_shortname(shortname) == expected_result


def test_get_subscriber_tags_and_extras():
    """Tests the ``get_subscriber_tags_and_extras`` function"""

    subscriber_tags, subscriber_extras = utils.get_subscriber_tags_and_extras('prod')

    for tag in subscriber_tags:
        assert tag[0] in str(subscriber_config['streams']['prod']['tags'])

    for extra in subscriber_extras:
        assert extra[0] in str(subscriber_config['streams']['prod']['extras'])


def test_get_tag_value():
    """Tests the ``get_tag_value`` function"""

    value = utils.get_tag_value('test_filename.txt', 'aperture')
    assert value == 'some_value'


def test_register_admin():
    """Tests the ``register_admin`` function"""

    utils.register_admin()

    # Check that there is an account entry
    account = query_for_account('lasp_admin')
    assert account


def test_set_unavailable():
    """Tests the ``set_as_unavailable`` function"""

    utils.set_as_unavailable(23456)

    results = db.session.query(db.Files).filter(db.Files.fileid == 23456).all()
    assert results[0].available == False


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
