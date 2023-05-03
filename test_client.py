"""This script performs various tests of the client side of the LASP SDTP
application.

The script sends PUT, GET, and DELETE requests to the application endpoints and
asserts that the responses have expected status codes.

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be executed via the command line as such:
    ::
        python test_client.py
"""

import datetime
import glob
from pathlib import Path
import requests

from lasp_sdtp.config import admin_config
from lasp_sdtp.database.controller import db
from lasp_sdtp.database.ingest import Ingest

from bin.create_test_filesystem import create_test_filesystem
from tests import conftest


def _ingest_files():
    """Ingests various files into the database for testing purposes."""

    print('Ingesting files into the database')
    filelist = glob.glob(str(Path(admin_config['filesystem_loc']) / 'prod' / '*'))
    production = Ingest(filelist, 'prod', '01')  # Ingest a 'production' stream of the data
    production.ingest()
    development = Ingest(filelist, 'dev', '01')  # Ingest a 'development' stream of the data
    development.ingest()


def _test_prep():
    """Creates test files and adds various database entries in order to support
    the tests within this module"""

    # Create a test filesystem if necessary
    test_directory = Path(admin_config['filesystem_loc']) / 'prod'
    test_files = glob.glob(f'{test_directory}/*')
    if not test_files:
        print('Creating test filesystem')
        create_test_filesystem()
    else:
        print(f'Test files found in {test_directory}')

    # Remove any data that may already exist in the database
    print('Removing existing database entries')
    db.session.query(db.FileQueue).delete()
    db.session.query(db.Transactions).delete()
    db.session.query(db.TagsAndExtras).delete()
    db.session.query(db.Files).delete()
    db.session.query(db.MissionShortnameMapping).delete()
    db.session.query(db.Shortnames).delete()
    db.session.query(db.MissionAccountMapping).delete()
    db.session.query(db.Missions).delete()
    db.session.query(db.Accounts).delete()
    db.session.commit()

    # Add entries to database tables to support tests
    print('Adding database entries to support testing')

    conftest._add_missions_entries()
    conftest._add_accounts_entries()
    conftest._add_shortnames_entries()
    conftest._add_mission_shortname_mapping_entries()

    # Add 'restricted' file to test with
    data_to_insert = [db.Files(
        fileid=99999,
        name='restricted_file.txt',
        checksum='fop',
        size=1,
        expires=datetime.datetime.utcnow().date() + datetime.timedelta(days=1),
        stream='prod',
        shortname='RESTRICTED',
        version='01',
        ingest_date=datetime.datetime.utcnow().date(),
        available=True
    )]
    db.insert_data(data_to_insert)


def test_api(method, url, expected_response, verbose=True):
    """Sends a request to the SDTP api and return its response.

    Parameters
    ----------
    method : str
        The method to use for the request (i.e. ``PUT``, ``GET``, or ``DELETE``)
    url : str
        The url to send the request to (e.g. ``http://127.0.0.1:8000/files``)
    expexted_response : int
        The expected status code of the response (e.g. ``200``)
    verbose : bool
        Turn on/off printing messages to the terminal
    """

    headers = {'Accept': 'application/json',
               'Cert-UID': 'ges_disc_cert'}

    if verbose:
        print(f'\nTrying {method} {url}')
    if method == 'PUT':
        response = requests.put(url, headers=headers)
    elif method == 'GET':
        response = requests.get(url, headers=headers)
    elif method == 'DELETE':
        response = requests.delete(url, headers=headers)
    if verbose:
        print(f'Response: '
              f'\n\t{response.status_code}'
              f'\n\t{response.text}')
    assert response.status_code == expected_response, f'Expected {expected_response} response, got {response.status_code}'

    return response


if __name__ == '__main__':

    print('\nRunning end-to-end test\n')

    # Do various preparations for testing (e.g. add database entries, ingest files, etc.)
    _test_prep()

    # Register Account
    test_api('PUT', 'http://127.0.0.1:8000/register', 204)

    # Ingest the test filesystem (thus adding entries to Files and FileQueue)
    _ingest_files()

    # Get a fileid to test with
    results = db.session.query(db.Files).first()
    fileid = results.fileid

    # Get filelist
    test_api('GET', 'http://127.0.0.1:8000/files', 200)
    test_api('GET', 'http://127.0.0.1:8000/files?shortname=TSIS2_SC_L2', 200)
    test_api('GET', 'http://127.0.0.1:8000/files?shortname=TSIS2_SC_L2&stream=dev', 200)
    test_api('GET', 'http://127.0.0.1:8000/files?shortname=TSIS2_SC_L2&stream=dev&irradiance=some_value', 200)
    test_api('GET', 'http://127.0.0.1:8000/files?startfileid=1&maxfile=3', 200)
    test_api('GET', 'http://127.0.0.1:8000/files?shortname=TSIS2_SC_L2&stream=dev&irradiance=some_value&startfileid=1&maxfile=3', 200)

    # Get file
    test_api('GET', f'http://127.0.0.1:8000/files/{fileid}', 200)

    # Delete file
    test_api('DELETE', f'http://127.0.0.1:8000/files/{fileid}', 204)

    # Delete range of files
    test_api('DELETE', f'http://127.0.0.1:8000/files/{fileid}-{fileid+3}', 204)

    # Send a request to endpoint that doesn't exist
    test_api('GET', 'http://127.0.0.1:8000/bogus_endpoint', 404)

    # Try to register a closed account
    test_api('PUT', 'http://127.0.0.1:8000/register', 401)  # The account should already be registered and thus not open for registration

    # Request a filelist with bogus parameters
    test_api('GET', 'http://127.0.0.1:8000/files?bogus_param=foo', 400)
    test_api('GET', 'http://127.0.0.1:8000/files?shortname=TSIS_SC_L2&bogus_param=foo', 400)

    # Request a filelist with valid parameters but no files returned
    test_api('GET', 'http://127.0.0.1:8000/files?shortname=foo', 200)

    # Request a file that doesn't exist
    test_api('GET', 'http://127.0.0.1:8000/files/1234567', 404)

    # Request a file with invalid fileid
    test_api('GET', 'http://127.0.0.1:8000/files/-1', 400)
    test_api('GET', 'http://127.0.0.1:8000/files/1.5', 400)
    test_api('GET', 'http://127.0.0.1:8000/files/foo', 400)
    test_api('GET', 'http://127.0.0.1:8000/files/9999999999999999', 400)

    # Try to delete a file that doesn't exist
    test_api('DELETE', 'http://127.0.0.1:8000/files/1234567', 404)

    # Try to delete a file with invalid fileid
    test_api('DELETE', 'http://127.0.0.1:8000/files/-1', 400)
    test_api('DELETE', 'http://127.0.0.1:8000/files/1.5', 400)
    test_api('DELETE', 'http://127.0.0.1:8000/files/foo', 400)
    test_api('DELETE', 'http://127.0.0.1:8000/files/9999999999999999', 400)

    # Try to delete a range of files that don't exist
    test_api('DELETE', 'http://127.0.0.1:8000/files/1234567-1234569', 404)

    # Try to delete a range of files with invalid fileids
    test_api('DELETE', 'http://127.0.0.1:8000/files/foo-bar', 400)
    test_api('DELETE', 'http://127.0.0.1:8000/files/10-5', 400)
    test_api('DELETE', 'http://127.0.0.1:8000/files/123-foo', 400)
    test_api('DELETE', 'http://127.0.0.1:8000/files/10-10', 400)

    # Try to request a file that user doesn't have access to (file 99999 is hard-coded to be restricted)
    test_api('GET', 'http://127.0.0.1:8000/files/99999', 403)

    # Try to delete a file that user doesn't have access to (file 99999 is hard-coded to be restricted)
    test_api('DELETE', 'http://127.0.0.1:8000/files/99999', 403)

    # Send multiple of requests at once
    # params = [
    #     ('GET', 'http://127.0.0.1:8000/files', 200),
    #     ('GET', 'http://127.0.0.1:8000/files', 200),
    #     ('GET', 'http://127.0.0.1:8000/files', 200),
    #     ('GET', 'http://127.0.0.1:8000/files', 200),
    #     ('GET', 'http://127.0.0.1:8000/files', 200),
    #     ('GET', 'http://127.0.0.1:8000/files', 200),
    #     ('GET', 'http://127.0.0.1:8000/files', 200),
    #     ('GET', 'http://127.0.0.1:8000/files', 200)
    # ]
    # pool = multiprocessing.Pool(processes=8)
    # pool.starmap(test_api, params)
    # pool.close()

    print('\nAll tests completed successfully!')
