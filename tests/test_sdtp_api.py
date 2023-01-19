"""Tests for the ``sdtp_api`` module.

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_api_gateway.py

TODO: Add test for parse_api_response (requires mock request)
"""

import datetime
import glob
import json
from pathlib import Path

import pytest
from flask.app import Flask
from flask.testing import FlaskClient
from werkzeug.datastructures import Headers

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db
from lasp_sdtp.database.database_queries import query_for_account_by_username
from lasp_sdtp.utils.properties import TEST_FILES_TO_IGNORE
from lasp_sdtp.server.ancillary import get_app
from lasp_sdtp.server.ancillary import register_admin


TEST_URLS = [
    '/files',
    '/files?stream=prod',
    '/files?stream=prod&shortname=TSIS2_L1',
    '/files?stream=foo']  # No files, but should still return 200

INVALID_TEST_URLS = [
    '/files?bogus_tag=foo',  # Invalid tag
    '/files/foo',  # fileid is not an integer 15 digits or fewer
    '/files/123.4',  # fileid is not an integer 15 digits or fewer
    '/files/-1',  # fileid is not an integer 15 digits or fewer
    '/files/1234567890123456']  # fileid is not an integer 15 digits or fewer


def _check_transaction(headers: Headers):
    """Checks that a transaction record was added to the ``transactions`` table

    Parameters
    ----------
    headers : ``werkzeug.datastructures.Headers`` obj
        The response header object
    """

    # Make sure the transaction ID is in the header
    assert 'SDTP-TransactionID' in headers

    # Check that there is a record in the transactions table
    results = db.session.query(
                  db.Transactions
              ).filter(
                  db.Transactions.transactionid == headers['SDTP-TransactionID']
              ).all()
    assert len(results) == 1  # There should only be one entry


@pytest.fixture()
def app() -> Flask:
    """Create an instance of the flask application to test with.

    Yields
    ------
    app : flask.app.Flask object
        The ``flask`` object for the application
    """

    app = get_app()
    app.config.update({'TESTING': True})

    yield app


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Create a test client from the ``flask`` app.  The ``client`` object is
    used to send requests to the server.

    Parameters
    ----------
    app : ``flask.app.Flask`` object
        The app from which to create a client

    Returns
    -------
    client : flask.testing.FlaskClient object
        The client object to test with
    """

    client = app.test_client()
    return client


def test_register(client: FlaskClient):
    """Tests that the ``PUT /register`` request works as expected

    Parameters
    ----------
    client : flask.testing.FlaskClient object
        The client to test with
    """

    # Clear out MissionAccountMapping to allow for the fields to be entered during registration
    db.session.query(db.MissionAccountMapping).filter(db.MissionAccountMapping.account == 'test_account').delete()
    db.session.commit()

    # Register the test account
    request_url = '/register'
    headers = {'content-type': 'application/json', 'Cert-UID': 'test_account_cert'}
    response = client.put(request_url, headers=headers)

    # Make sure the response is correct
    assert response.status_code == 204

    # Check that a database entry was made for the Accounts table and that it has registered
    results = db.session.query(db.Accounts).filter(db.Accounts.username == 'test_account').all()
    assert len(results) == 1  # There should only be one entry
    assert results[0].__dict__['username'] == subscriber_config['username']
    assert results[0].__dict__['registration_open'] == 0
    assert results[0].__dict__['registration_date'].date() == datetime.datetime.utcnow().date()

    _check_transaction(response.headers)


def test_register_admin():
    """Tests the ``register_admin`` function"""

    register_admin()

    # Check that there is an account entry
    account = query_for_account_by_username('lasp_admin')
    assert account


def test_authorize(client: FlaskClient):
    """Tests the ``authorize`` function

    Parameters
    ----------
    client : flask.testing.FlaskClient object
        The client to test with
    """

    # For authenticated requests
    authorized_headers = {'content-type': 'application/json', 'Cert-UID': 'test_account_cert'}
    authorized_response = client.get('/files', headers=authorized_headers)
    assert authorized_response.status_code == 200

    # For unauthorized GET request
    unauthorized_headers = {'content-type': 'application/json', 'Cert-UID': 'fake_certificate'}
    unauthorized_get_response = client.get('/files', headers=unauthorized_headers)
    data = json.loads(unauthorized_get_response.get_data().decode("utf-8"))
    assert data['message'] == 'Request is not authenticated'

    # For unauthorized PUT request
    unauthorized_put_response = client.put('/register', headers=unauthorized_headers)
    assert unauthorized_put_response.status_code == 401
    data = json.loads(unauthorized_put_response.get_data().decode("utf-8"))
    assert data['message'] == 'Unauthorized'


@pytest.mark.parametrize('request_url', TEST_URLS)
def test_get_filelist(client: FlaskClient, request_url: str):
    """Tests that the ``GET /files`` request works as expected

    Parameters
    ----------
    client : flask.testing.FlaskClient object
        The client to test with
    request_url : str
        The request url to test (e.g. ``/files``)
    """

    # Send a test request and get the response
    headers = {'content-type': 'application/json', 'Cert-UID': 'test_account_cert'}
    response = client.get(request_url, headers=headers)
    data = json.loads(response.get_data().decode("utf-8"))

    # Make sure the response status is 200
    assert response.status_code == 200

    # Check if the returned files are in the filesystem
    test_files = glob.glob(str(Path(admin_config['filesystem_loc']) / 'prod' / '*'))
    for entry in data['files']:
        filename = Path(admin_config['filesystem_loc']) / 'prod' / entry['name']
        if filename.name not in TEST_FILES_TO_IGNORE:
            assert str(filename) in test_files

    _check_transaction(response.headers)


def test_get_filelist_filter_by_tag(client: FlaskClient):
    """Tests that the ``GET /files`` request works as expected when filtering
    results with subscriber-provided tags"""

    request_url = '/files?observation_date=some_value'

    # Send a test request and get the response
    headers = {'content-type': 'application/json', 'Cert-UID': 'test_account_cert'}
    response = client.get(request_url, headers=headers)
    data = json.loads(response.get_data().decode("utf-8"))

    # Make sure the response status is 200
    assert response.status_code == 200

    # Make sure the results are as expected
    assert len(data['files']) == 59
    for file in data['files']:
        assert 'observation_date' in file['tags']


def test_get_filelist_with_pagination(client: FlaskClient):
    """Tests that the ``GET /files`` request works as expected with pagination
    parameters"""

    startfileid = 10000
    maxfile = 3
    request_url = f'/files?startfileid={startfileid}&maxfile={maxfile}'

    # Send a test request and get the response
    headers = {'content-type': 'application/json', 'Cert-UID': 'test_account_cert'}
    response = client.get(request_url, headers=headers)
    data = json.loads(response.get_data().decode("utf-8"))

    # Make sure the response status is 200
    assert response.status_code == 200

    # Make sure the results are as expected
    assert len(data['files']) == maxfile
    assert min([item['fileid'] for item in data['files']]) >= startfileid


def test_get_file(client: FlaskClient):
    """Tests that the ``GET /files/<fileid>`` request works as expected

    Parameters
    ----------
    client : flask.testing.FlaskClient object
        The client to test with
    """

    # Get the lowest fileid that exists
    available_files = db.session.query(db.Files).filter(db.Files.available == True).order_by(db.Files.fileid).all()
    fileid = str(available_files[0].__dict__['fileid'])

    # Send a request and get the response
    request_url = f'/files/{fileid}'
    headers = {'content-type': 'application/json', 'Cert-UID': 'test_account_cert'}
    response = client.get(request_url, headers=headers)
    data = json.loads(response.get_data().decode("utf-8"))

    # Make sure the response status is 200
    assert response.status_code == 200

    # Check if the file is in the subscriber queue staging area
    filepath = Path(admin_config['staging_loc']) / 'test_account' / 'prod' / data['filename']
    assert filepath.exists()

    _check_transaction(response.headers)


def test_delete_file(client: FlaskClient):
    """Tests that the ``DELETE /files/<fileid>`` request works as expected

    Parameters
    ----------
    client : flask.testing.FlaskClient object
        The client to test with
    """

    # Get the lowest fileid that exists
    available_files = db.session.query(db.Files).filter(db.Files.available == True).order_by(db.Files.fileid).all()
    fileid = str(available_files[0].__dict__['fileid'])

    # Delete the file
    request_url = f'files/{fileid}'
    headers = {'content-type': 'application/json', 'Cert-UID': 'test_account_cert'}
    response = client.delete(request_url, headers=headers)

    # Make sure the response status is 204
    assert response.status_code == 204

    # Check that the database entry was removed
    results = db.session.query(db.FileQueue).filter(db.FileQueue.fileid == fileid).all()
    assert len(results) == 0

    _check_transaction(response.headers)


def test_delete_files(client: FlaskClient):
    """Tests that the ``DELETE /files/<fileid_start>-<fileid_end>`` request
    works as expected

    Parameters
    ----------
    client : flask.testing.FlaskClient object
        The client to test with
    """

    headers = {'content-type': 'application/json', 'Cert-UID': 'test_account_cert'}

    # Get a handful of files to test
    available_files = db.session.query(db.Files).filter(db.Files.available == True).order_by(db.Files.fileid).all()
    fileid_start = available_files[0].__dict__['fileid']
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
        results = db.session.query(db.FileQueue).filter(db.FileQueue.fileid == fileid).all()
        assert len(results) == 0


def test_unauthorized_request(client: FlaskClient):
    """Tests that an unauthorized request returns the expected response of 401

    Parameters
    ----------
    client : flask.testing.FlaskClient object
        The client to test with
    """

    request_url = '/files'
    headers = {'content-type': 'application/json', 'Cert-UID': 'bogus_cert'}
    response = client.get(request_url, headers=headers)
    data = json.loads(response.get_data().decode("utf-8"))

    assert response.status_code == 401
    assert data['message'] == 'Request is not authenticated'


@pytest.mark.parametrize('request_url', INVALID_TEST_URLS)
def test_incorrect_requests(client: FlaskClient, request_url: str):
    """Tests that incorrect ``GET /files`` requests return the expected response
    of 400

    Parameters
    ----------
    client : flask.testing.FlaskClient object
        The client to test with
    request_url : str
        The request url to test (e.g. ``/files?start_date=2022-01-01``)
    """

    # Send the request and get the response
    headers = {'content-type': 'application/json', 'Cert-UID': f'{subscriber_config["username"]}_cert'}
    response = client.get(request_url, headers=headers)
    data = json.loads(response.get_data().decode("utf-8"))

    # Make sure the response is correct
    assert response.status_code == 400
    assert data['message'] == 'The request is incorrect'


def test_file_does_not_exist(client: FlaskClient):
    """Tests that a ``GET /files/{fileid}`` and a ``DELETE /files/{fileid}``
    request for a file that doesn't exist returns the expected response of 404

    Parameters
    ----------
    client : flask.testing.FlaskClient object
        The client to test with
    """

    request_url = '/files/999999999999999'
    headers = {'content-type': 'application/json', 'Cert-UID': 'test_account_cert'}

    for method in ['get', 'delete']:
        response = getattr(client, method)(request_url, headers=headers)

        data = json.loads(response.get_data().decode("utf-8"))

        # Make sure the response is correct
        assert response.status_code == 404
        assert data['message'] == 'The requested resource does not exist'
