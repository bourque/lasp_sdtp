"""Tests for ``database_interface.py``

Authors
-------
    Matthew Bourque

Use
---
    pytest test_database_interface.py
"""

import pytest
from sqlalchemy import Table

from lasp_sdtp.database.database_interface import base, session


def test_db_connection():
    """Tests that the test database can be connected to"""

    assert 'oracle://' in str(session.bind.url)


def test_fileid_boundary():

    table = Table('file_metadata', base.metadata)

    data = {
        'fileid': 9999999999999999,  # 16 digits
        'name': 'foo',
        'checksum': 'foo',
        'size': 1,
        'expires': '2022-12-31',
        'stream': 'prod',
        'shortname': 'foo',
        'version': '001'
    }

    # Insert data into database
    with pytest.raises(Exception) as error:
        table.insert().execute([data])
    assert 'ORA-01438' in str(error.value)  # ORA-01438: value larger than specified precision allowed


def test_update_transactions_table():
    """
    """

    pass
