"""Tests for app

Authors
-------
    Matthew Bourque

Use
---
    pytest test_run_server.py
"""

import glob
import os
import pytest

from lasp_sdtp.database.database_interface import base, engine, FileMetadata, insert_test_data, session
from lasp_sdtp.server.run_server import create_app

HOME_DIR = os.path.expanduser('~')

@pytest.fixture()
def app():
    app = create_app()
    app.config.update({'TESTING': True,})

    # Clear out test database
    base.metadata.drop_all()
    base.metadata.create_all(engine)

    # Add testing data to test database
    insert_test_data()

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_db_connection(client):

    assert os.path.basename(str(session.bind.url)) == 'lasp_sdtp_db.db'


def test_get_filelist(client):

    response = client.get('/files?stream=prod&ShortName=TSIS2_L1')

    test_filesystem = f'{HOME_DIR}/Desktop/test_filesystem/'
    test_files = glob.glob(os.path.join(test_filesystem, '*'))

    for test_file in test_files:
        if os.path.basename(test_file).startswith('tsis2_L1'):
            assert os.path.basename(test_file) in str(response.data)

def test_get_file(client):
    
    response = client.get('/files/1')
    assert 'contents' in str(response.data)

def test_delete_file(client):
    
    response = client.delete('files/1')
    assert 'File to delete' in str(response.data)

def test_delete_files(client):
    pass

def test_register(client):
    
    response = client.put('/register')
    assert '"status":200' in str(response.data)
