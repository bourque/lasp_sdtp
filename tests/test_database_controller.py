"""Tests for the ``database_controller.py`` module.

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_database_interface.py
"""

import datetime
from collections import namedtuple

import pytest

from lasp_sdtp.database.database_controller import db


def test_connect():
    """Tests the ``load_connection`` method"""

    _session, _base, _engine, _meta = db._connect()
    assert 'oracle://' in str(_session.bind.url)


def test_delete_file_from_queue():
    """Tests the ``delete_file_from_queue`` method"""

    # Delete a file from the queue
    fileid = 78901
    db.delete_file_from_queue(fileid)

    # Check that there is no record in the file_queue table
    results = db.session.query(db.FileQueue).filter(db.FileQueue.fileid == fileid).all()
    assert len(results) == 0


def test_fileid_boundary():
    """Tests that the ``fileid`` cannot exceed 15 digits"""

    data = [db.Files(
        fileid=9999999999999999,  # 16 digits
        name='foo',
        checksum='foo',
        size=1,
        expires=datetime.datetime.utcnow().date(),
        stream='prod',
        shortname='TSIS2_L1',
        version='01',
        ingest_date=datetime.datetime.utcnow().date(),
        available=True
    )]

    # Try to insert data into database
    with pytest.raises(Exception) as error:
        db.insert_data(data)
    assert 'ORA-01438' in str(error.value)  # ORA-01438: value larger than specified precision allowed
    db.session.rollback()


def test_insert_data():
    """Tests the ``insert_data`` method"""

    data = [db.Files(
        fileid=98765,
        name='insert_data.txt',
        checksum='hash',
        size=1,
        expires=datetime.datetime.utcnow().date(),
        stream='prod',
        shortname='TSIS2_L1',
        version='01',
        ingest_date=datetime.datetime.utcnow().date(),
        available=True
    )]
    db.insert_data(data)

    results = db.session.query(db.Files).filter(db.Files.fileid == 98765).all()
    assert len(results) == 1  # There should only be one entry


def test_update_transactions_table():
    """Tests the ``update_transactions_table`` method"""

    # Get the lowest fileid that exists
    files = db.session.query(db.Files).filter().order_by(db.Files.fileid).all()
    test_fileid = str(files[0].__dict__['fileid'])

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
