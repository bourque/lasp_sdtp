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
from lasp_sdtp.database.database_controller import db


def test_connect():
    """Tests the ``load_connection`` function"""

    _session, _base, _engine, _meta = db.connect()
    assert 'oracle://' in str(_session.bind.url)


def test_fileid_boundary():
    """Tests that the ``fileid`` cannot exceed 15 digits"""

    table = Table('file_metadata', db.base.metadata)

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
    """Tests the ``update_transactions_table`` function"""

    # Get the lowest fileid that exists
    file_metadata = db.session.query(db.FileMetadata).filter().order_by(db.FileMetadata.fileid).all()
    test_fileid = str(file_metadata[0].__dict__['fileid'])

    # Create dummy requests
    Request = namedtuple('request', ['method', 'url'])
    requests = [Request('PUT', '/register'),
                Request('GET', '/files'),
                Request('GET', f'/files/{test_fileid}'),
                Request('DELETE', f'/files/{test_fileid}')]
    fileids = [None, None, test_fileid, test_fileid]

    for request, fileid in zip(requests, fileids):

        transactionid = db.update_transactions_table(request, fileid)

        # Check that there is a record in the transactions table
        results = db.session.query(db.Transactions).filter(db.Transactions.transactionid == transactionid).all()
        assert len(results) == 1  # There should only be one entry
        assert request.url in results[0].__dict__['action']

        # Remove account entry so that it doesn't break future tests
        if request.method == 'DELETE':
            db.session.query(db.Transactions).filter(db.Transactions.username == subscriber_config['username']).delete()
            db.session.query(db.Accounts).filter(db.Accounts.username == subscriber_config['username']).delete()
            db.session.commit()
