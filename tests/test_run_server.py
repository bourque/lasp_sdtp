"""Tests for ``run_server.py``

Authors
-------
    Matthew Bourque

Use
---
    pytest test_run_server.py
"""

import glob
import json
import os

import pytest

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_interface import Accounts
from lasp_sdtp.database.database_interface import FileMetadata
from lasp_sdtp.database.database_interface import FileQueue
from lasp_sdtp.database.database_interface import session
from lasp_sdtp.database.database_interface import Transactions
from lasp_sdtp.server.run_server import get_app


TEST_URLS = [
    '/files',
    '/files?stream=prod',
    '/files?stream=prod&ShortName=TSIS2_L1',
    '/files?date=2022-01-01',
    '/files?start_date=2022-01-01&end_date=2022-02-01']


def _check_transaction(request_url, headers):
    """Checks that a transaction record was added to the database

    Parameters
    ----------
    request_url : str
        The request URL (e.g. ``'/files?stream=prod&ShortName=TSIS2_L1'``)
    headers : ``werkzeug.datastructures.Headers`` obj
        The response header object
    """

    # Make sure the transactionid is in the header
    assert 'SDTP-TransactionID' in headers

    # Check that there is a record in the transactions table
    results = session.query(Transactions).filter(Transactions.transactionid == headers['SDTP-TransactionID']).all()
    assert len(results) == 1  # There should only be one db entry
    assert request_url in results[0].__dict__['action']


@pytest.fixture()
def app():
    """Create an instance of the application to test with.  Also perform any
    necessary build up and tear down needed to run the tests.

    Yeilds
    ------
    app : flask.app.Flask object
        The ``flask`` object for the application
    """

    app = get_app()
    app.config.update({'TESTING': True})

    yield app


@pytest.fixture()
def client(app):
    """Create a test client from the ``flask`` app

    Returns
    -------
    client : flask.testing.FlaskClient object
        The client to test with
    """

    client = app.test_client()
    return client


def test_register(client):
    """Tests that the ``PUT /register`` request works as expected"""

    request_url = '/register'
    headers = {'content-type': 'application/json', 'Cert-UID': f'{subscriber_config["username"]}_cert'}
    response = client.put(request_url, headers=headers)

    # Make sure the response status is 200
    assert response.status_code == 200

    # Check that a database entry was made for the Accounts table
    results = session.query(Accounts).filter(Accounts.username == subscriber_config['username']).all()
    assert len(results) == 1  # There should only be one db entry
    assert results[0].__dict__['username'] == subscriber_config['username']

    _check_transaction(request_url, response.headers)


def test_authorize(client):
    """Tests the ``authorize`` function"""

    request_url = '/files'
    authorized_headers = {'content-type': 'application/json', 'Cert-UID': f'{subscriber_config["username"]}_cert'}
    bogus_headers = {'content-type': 'application/json', 'Cert-UID': 'fake_certificate'}

    authorized_response = client.get(request_url, headers=authorized_headers)
    bogus_response = client.get(request_url, headers=bogus_headers)

    assert authorized_response.status_code == 200
    assert bogus_response.status_code == 401


@pytest.mark.parametrize('request_url', TEST_URLS)
def test_get_filelist(client, request_url):
    """Tests that the ``GET /files`` request works as expected"""

    # Send a test request and get the response
    headers = {'content-type': 'application/json', 'Cert-UID': f'{subscriber_config["username"]}_cert'}
    response = client.get(request_url, headers=headers)
    data = json.loads(response.get_data().decode("utf-8"))

    # Make sure the response status is 200
    assert response.status_code == 200

    # Check if the returned files are in the filesystem
    test_files = glob.glob(os.path.join(admin_config['filesystem_loc'], '*'))
    for entry in data['files']:
        filename = os.path.join(admin_config['filesystem_loc'], entry['name'])
        if 'test_cleanup_db' not in filename and 'test_reporting' not in filename:  # ignore files used in other tests
            assert filename in test_files 

    _check_transaction(request_url, response.headers)


def test_get_file(client):
    """Tests that the ``GET /files/<fileid>`` request works as expected"""

    # Get the lowest fileid that exists
    file_metadata = session.query(FileMetadata).filter().order_by(FileMetadata.fileid).all()
    fileid = str(file_metadata[0].__dict__['fileid'])

    # Send a test request and get the response
    request_url = f'/files/{fileid}'
    headers = {'content-type': 'application/json', 'Cert-UID': f'{subscriber_config["username"]}_cert'}
    response = client.get(request_url, headers=headers)
    data = json.loads(response.get_data().decode("utf-8"))

    # Make sure the response status is 200
    assert response.status_code == 200

    # Check if the file is in the queue
    assert os.path.exists(os.path.join(admin_config['subscriber_queues_loc'], subscriber_config['username'], data['filename']))

    # Check that there is a database entry for the file in the queue
    results = session.query(FileQueue).filter(FileQueue.fileid == fileid).all()
    assert len(results) == 1  # There should only be one db entry
    assert results[0].__dict__['fileid'] == int(fileid)

    _check_transaction(request_url, response.headers)


def test_delete_file(client):
    """Tests that the ``DELETE /files/<fileid>`` request works as expected"""

    # Get the lowest fileid that exists
    file_metadata = session.query(FileMetadata).filter().order_by(FileMetadata.fileid).all()
    fileid = str(file_metadata[0].__dict__['fileid'])

    # Delete the file
    request_url = f'files/{fileid}'
    headers = {'content-type': 'application/json', 'Cert-UID': f'{subscriber_config["username"]}_cert'}
    response = client.delete(request_url, headers=headers)

    # Make sure the response status is 204
    assert response.status_code == 204

    # Check that the database entry was removed
    results = session.query(FileQueue).filter(FileQueue.fileid == fileid).all()
    assert len(results) == 0

    _check_transaction(request_url, response.headers)


def test_delete_files(client):
    """Tests that the ``DELETE /files/<fileid_start>-<fileid_end>`` request
    works as expected
    """

    headers = {'content-type': 'application/json', 'Cert-UID': f'{subscriber_config["username"]}_cert'}

    # Get a handful of files to test
    file_metadata = session.query(FileMetadata).filter().order_by(FileMetadata.fileid).all()
    fileid_start = file_metadata[0].__dict__['fileid']
    fileid_end = fileid_start + 5
    fileids = [fileid for fileid in range(fileid_start, fileid_end)]
    for fileid in fileids:
        client.get(f'/files/{str(fileid)}', headers=headers)

    # Delete the files
    request_url = f'/files/{fileid_start}-{fileid_end}'
    response = client.delete(request_url, headers=headers)

    # Make sure the response status is 204
    assert response.status_code == 204

    # Check that the database entries were removed
    for fileid in fileids:
        results = session.query(FileQueue).filter(FileQueue.fileid == fileid).all()
        assert len(results) == 0
