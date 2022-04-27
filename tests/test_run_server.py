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

from lasp_sdtp.database.database_interface import base, engine, insert_test_data, session
from lasp_sdtp.server.run_server import get_app

HOME_DIR = os.path.expanduser('~')
SUBSCRIBER_QUEUE = f'{HOME_DIR}/Desktop/test_queue/'


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

    # Clear out test database
    #base.metadata.drop_all()
    #base.metadata.create_all(engine)

    # Add testing data to test database
    #insert_test_data()

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


def test_db_connection(client):
    """Tests that the test database can be connected to"""

    assert 'oracle://' in str(session.bind.url)


def test_get_filelist(client):
    """Tests that the ``GET /files`` request works as expected"""

    # Send a test request and get the response
    response = client.get('/files?stream=prod&ShortName=TSIS2_L1')
    data = json.loads(response.data)

    # Make sure the response status is 200
    assert data['status'] == 200

    # Check if the returned files are in the filesystem
    test_filesystem = f'{HOME_DIR}/Desktop/test_filesystem/'
    test_files = glob.glob(os.path.join(test_filesystem, '*'))
    for test_file in test_files:
        if os.path.basename(test_file).startswith('tsis2_L1'):
            assert os.path.basename(test_file) in str(data['files'])

    # Make sure the response headers are correct


def test_get_file(client):
    """Tests that the ``GET /files/<fileid>`` request works as expected"""
    
    # Send a test request and get the response
    response = client.get('/files/1')
    data = json.loads(response.data)

    # Make sure the response status is 200
    assert data['status'] == 200

    # Check if the file is in the queue
    assert os.path.exists(os.path.join(SUBSCRIBER_QUEUE, data['filename']))

    # Check that there is a database entry for the file in the queue

    # Make sure the response headers are correct


def test_delete_file(client):
    """Tests that the ``DELETE /files/<fileid>`` request works as expected"""
    
    response = client.delete('files/1')
    data = json.loads(response.data)

    # Make sure the response status is 204
    assert data['status'] == 204


def test_delete_files(client):
    """Tests that the ``DELETE /files/<fileid_start>-<fileid_end>`` request
    works as expected"""
    pass


def test_register(client):
    """Tests that the ``PUT /register`` request works as expected"""
    
    response = client.put('/register')
    assert '"status":200' in str(response.data)
