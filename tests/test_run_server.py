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
import random
import string

from sqlalchemy import Table

from lasp_sdtp.config import config
from lasp_sdtp.database.database_interface import base, FileMetadata, FileQueue, session
from lasp_sdtp.server.run_server import get_app

HOME_DIR = os.path.expanduser('~')
SUBSCRIBER_QUEUE = f'{HOME_DIR}/Desktop/test_queue/'


def _get_checksum():
    """Return a randomly generated checksum

    Returns
    -------
    checksum : str
        A randomly generated checksum based on the ``checksum_type`` given in
        the system configuration
    """

    checksum_type = config['checksum_type']
    checksum_string = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(64))
    checksum = f'{checksum_type}:{checksum_string}'

    return checksum


def _get_shortname(filename):
    """Return the appropriate ``ShortName`` for the given filename.

    Parameters
    ----------
    filename : str
        The filename of interest (e.g. ``tsis2_tim_L2_v01_20220422.zip``)

    Returns
    -------
    shortname : str
        The ``ShortName`` that matches the given filename (e.g. ``TSIS2_TIM_L2``)
    """

    shortname_mapping = {
        'tsis2_L1': 'TSIS2_L1',
        'tsis2_sim_cal': 'TSIS2_SIM_CAL',
        'tsis2_tim_cal': 'TSIS2_TIM_CAL',
        'tsis2_sim_L2': 'TSIS2_SIM_L2',
        'tsis2_tim_L2': 'TSIS2_TIM_L2',
        'tsis2_sc_L2': 'TSIS_SC_L2',
        'tsis2_ssi_L3_c12h': 'TSIS2_SSI_L3_12HR',
        'tsis2_ssi_L3_c24h': 'TSIS2_SSI_L3_24HR',
        'tsis2_tsi_L3_c06h': 'TSIS2_TSI_L3_06HR',
        'tsis2_tsi_L3_c24h': 'TSIS2_TSI_L3_24HR'
    }

    for item in shortname_mapping:
        if filename.startswith(item):
            shortname = shortname_mapping[item]
            if filename.endswith('.txt'):
                shortname += '_TXT'
            elif filename.endswith('.nc'):
                shortname += '_NC'

    return shortname


def _insert_test_data():
    """Insert test data into the test database. The data that are insterted is
    based on which files exist in the ``test_filesystem``
    """

    # Remove any data that already exists
    session.query(FileMetadata).delete()
    session.commit()
    session.query(FileQueue).delete()
    session.commit()

    table = Table('file_metadata', base.metadata)

    # Locate test files
    test_filesystem = f'{HOME_DIR}/Desktop/test_filesystem/'
    test_files = glob.glob(os.path.join(test_filesystem, '*'))

    # Gather metadata to store in database
    data_to_insert = []
    for i, test_file in enumerate(test_files):
        data = {
            'name': os.path.basename(test_file),
            'checksum': _get_checksum(),
            'size': os.path.getsize(test_file),
            'expires': '2022-12-31',
            'stream': 'prod',
            'shortname': _get_shortname(os.path.basename(test_file)),
            'version': '001'
        }
        data_to_insert.append(data)

    # Insert data into database
    table.insert().execute(data_to_insert)


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

    # Add testing data to test database
    _insert_test_data()

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

    # Get the lowest fileid that exists
    file_metadata = session.query(FileMetadata).filter().order_by(FileMetadata.fileid).all()
    fileid = str(file_metadata[0].__dict__['fileid'])

    # Send a test request and get the response
    response = client.get(f'/files/{fileid}')
    data = json.loads(response.data)

    # Make sure the response status is 200
    assert data['status'] == 200

    # Check if the file is in the queue
    assert os.path.exists(os.path.join(SUBSCRIBER_QUEUE, data['filename']))

    # Check that there is a database entry for the file in the queue

    # Make sure the response headers are correct


def test_delete_file(client):
    """Tests that the ``DELETE /files/<fileid>`` request works as expected"""

    # Get the lowest fileid that exists
    file_metadata = session.query(FileMetadata).filter().order_by(FileMetadata.fileid).all()
    fileid = str(file_metadata[0].__dict__['fileid'])

    response = client.delete(f'files/{fileid}')
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
