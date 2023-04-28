"""Tests for the ``database_queries.py`` module.

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_database_queries.py
"""

from lasp_sdtp.database.queries import query_for_account_by_username
from lasp_sdtp.database.queries import query_for_file
from lasp_sdtp.database.queries import query_for_filelist
from lasp_sdtp.database.queries import query_for_queue_entries
from lasp_sdtp.database.queries import validate_access


def test_query_for_account():
    """Tests the ``query_for_account`` method"""

    account = query_for_account_by_username('test_account')
    assert account['username'] == 'test_account'


def test_query_for_file():
    """Tests the ``query_for_available_files`` method"""

    metadata = query_for_file(98765)
    assert metadata.name == 'insert_data.txt'


def test_query_for_filelist():
    """Tests the ``query_for_filelist`` method"""

    tags = {
        'stream': 'prod',
        'version': '01',
        'shortname': 'TSIS2_L1'}
    filelist = query_for_filelist(tags=tags)
    assert len(filelist) == 12


def test_query_for_queue_entries():
    """Tests the ``query_for_queue_entries`` method"""

    queue_entries = query_for_queue_entries(67890)
    assert len(queue_entries) > 0


def test_validate_access():
    """Tests the ``validate_access`` function"""

    assert validate_access(12345) is True  # This is a tsis2 data product which the 'ges_disc' user has access to
    assert validate_access(23456) is False  # This is a 'restricted' data product
