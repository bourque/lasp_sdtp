"""Tests for ``database_interface.py``

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_database_interface.py
"""

from collections import namedtuple

import pytest
from sqlalchemy import Table

from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_interface import Accounts
from lasp_sdtp.database.database_interface import base
from lasp_sdtp.database.database_interface import FileMetadata
from lasp_sdtp.database.database_interface import load_connection
from lasp_sdtp.database.database_interface import session
from lasp_sdtp.database.database_interface import Transactions
from lasp_sdtp.database.database_interface import _update_transactions_table


def test_load_connection():
    """Tests the ``load_connection`` function"""

    session, base, engine, meta = load_connection()
    assert 'oracle://' in str(session.bind.url)


def test_fileid_boundary():
    """Tests that the ``fileid`` cannot exceed 15 digits"""

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

    # Try to insert data into database
    with pytest.raises(Exception) as error:
        table.insert().execute([data])
    assert 'ORA-01438' in str(error.value)  # ORA-01438: value larger than specified precision allowed


def test_update_transactions_table():
    """Tests the ``_update_transactions_table`` function"""

    # Get the lowest fileid that exists
    file_metadata = session.query(FileMetadata).filter().order_by(FileMetadata.fileid).all()
    test_fileid = str(file_metadata[0].__dict__['fileid'])

    # Create dummy requests
    Request = namedtuple('request', ['method', 'url'])
    requests = [Request('PUT', '/register'),
                Request('GET', '/files'),
                Request('GET', f'/files/{test_fileid}'),
                Request('DELETE', f'/files/{test_fileid}')]
    fileids = [None, None, test_fileid, test_fileid]

    for request, fileid in zip(requests, fileids):

        transactionid = _update_transactions_table(request, fileid)

        # Check that there is a record in the transactions table
        results = session.query(Transactions).filter(Transactions.transactionid == transactionid).all()
        assert len(results) == 1  # There should only be one entry
        assert request.url in results[0].__dict__['action']

        # Remove account entry so that it doesn't break future tests
        if request.method == 'DELETE':
            session.query(Transactions).filter(Transactions.username == subscriber_config['username']).delete()
            session.query(Accounts).filter(Accounts.username == subscriber_config['username']).delete()
            session.commit()
