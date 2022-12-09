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

from lasp_sdtp.database.database_queries import query_for_account
from lasp_sdtp.database.database_queries import query_for_filelist
from lasp_sdtp.database.database_queries import query_for_file
from lasp_sdtp.database.database_queries import query_for_queue_entries


def test_query_for_account():
    """Tests the ``query_for_account`` method"""

    account = query_for_account('test_account')
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
    assert len(filelist) == 10


def test_query_for_queue_entries():
    """Tests the ``query_for_queue_entries`` method"""

    queue_entries = query_for_queue_entries(67890)
    assert len(queue_entries) > 0
