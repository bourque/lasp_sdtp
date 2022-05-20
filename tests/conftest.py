"""This module contains code to perform setup and teardown needed to run the
test suite contained within the ``tests`` directory.  This module gets executed
before any tests when using ``pytest -s .``

Authors
-------
    Matthew Bourque
"""

import datetime
import glob
import random
import os

import pytest

from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_interface import Accounts
from lasp_sdtp.database.database_interface import FileMetadata
from lasp_sdtp.database.database_interface import FileQueue
from lasp_sdtp.database.database_interface import insert_data
from lasp_sdtp.database.database_interface import session
from lasp_sdtp.database.database_interface import Transactions
from lasp_sdtp.utils.utils import get_checksum
from lasp_sdtp.utils.utils import get_shortname

HOME_DIR = os.path.expanduser('~')
FILESYSTEM_PATH = f'{HOME_DIR}/Desktop/test_filesystem/'
SUBSCRIBER_QUEUE = f'{HOME_DIR}/Desktop/test_queue/'


def _add_accounts_entries():
    """Add necessary ``accounts`` table entries used for testing"""

    # Nominal test account for general testing
    data_to_insert = [{
        'username': 'test_account',
        'certuid': 'test_cert',
        'role': 'subscriber',
        'registration_date': datetime.datetime.today(),
        'registration_expires': datetime.datetime.today() + datetime.timedelta(days=1)}]

    # Add an entry for the subscriber (for test_database_interface)
    data_to_insert.append({
        'username': subscriber_config['username'],
        'certuid': 'test_cert',
        'role': 'subscriber',
        'registration_date': datetime.datetime.today(),
        'registration_expires': datetime.datetime.today() + datetime.timedelta(days=1)}
    )

    # Add an entry that has expired (for test_cleanup_database)
    data_to_insert.append({
        'username': 'expired_account',
        'certuid': 'test_cert',
        'role': 'subscriber',
        'registration_date': datetime.datetime.today(),
        'registration_expires': datetime.datetime.today() - datetime.timedelta(days=1)}
    )

    insert_data('accounts', data_to_insert)


def _add_file_metadata_entries():
    """Add necessary ``file_metadata`` table entries used for testing"""

    # Locate test files
    test_filesystem = f'{HOME_DIR}/Desktop/test_filesystem/'
    test_files = glob.glob(os.path.join(test_filesystem, '*'))

    # Insert filesystem data (mostly used for test_run_server)
    data_to_insert = []
    for i, test_file in enumerate(test_files):
        data = {
            'name': os.path.basename(test_file),
            'checksum': get_checksum(),
            'size': os.path.getsize(test_file),
            'expires': datetime.datetime.today() + datetime.timedelta(days=subscriber_config['expiration_period']),
            'stream': 'prod',
            'shortname': get_shortname(os.path.basename(test_file)),
            'version': 'v01',
            'date': datetime.datetime(2022, 1, 1) + datetime.timedelta(days=i-1)
        }
        data_to_insert.append(data)
    insert_data('file_metadata', data_to_insert)

    # to satisfy integrity contraint for test_cleanup_database
    data_to_insert = [{
        'fileid': 12345,
        'name': 'test_cleanup_db.txt',
        'checksum': 'foo',
        'size': 1,
        'expires': datetime.datetime.today() + datetime.timedelta(days=1),
        'stream': 'prod',
        'shortname': 'TEST_FILE',
        'version': 'v01',
        'date': datetime.datetime(2022, 1, 1)
    }]

    # to satisfy integrity contraint for test_cleanup_database
    data_to_insert.append({
        'fileid': 12346,
        'name': 'test_cleanup_db_2.txt',
        'checksum': 'bar',
        'size': 1,
        'expires': datetime.datetime.today() + datetime.timedelta(days=1),
        'stream': 'prod',
        'shortname': 'TEST_FILE',
        'version': 'v01',
        'date': datetime.datetime(2022, 1, 1)
    })

    # to satisfy integrity contraint for test_reporting
    data_to_insert.append({
        'fileid': 67890,
        'name': 'test_reporting.txt',
        'checksum': 'bop',
        'size': 1,
        'expires': datetime.datetime.today() + datetime.timedelta(days=1),
        'stream': 'prod',
        'shortname': 'TEST_FILE',
        'version': 'v01',
        'date': datetime.datetime(2022, 1, 1)
    })

    # A seperate call to insert_data() is needed so that the correct fileids are inserted
    insert_data('file_metadata', data_to_insert)


def _add_file_queue_entries():
    """Add necessary ``file_queue`` table entries used for testing"""

    # Add a file queue entry associated with the expired account (for test_cleanup_database)
    data_to_insert = [{
        'username': 'expired_account',
        'fileid': 12345,
        'entry_date': datetime.datetime.today(),
        'expires': datetime.datetime.today() - datetime.timedelta(days=10)
    }]

    # Add a file queue entry not associated with the expired account (for test_cleanup_database)
    data_to_insert.append({
        'username': 'test_account',
        'fileid': 12346,
        'entry_date': datetime.datetime.today(),
        'expires': datetime.datetime.today() - datetime.timedelta(days=10)
    })

    # Add an expired file to the file queue storage associated with expired account (for test_cleanup_database)
    with open(os.path.join(SUBSCRIBER_QUEUE, 'test_cleanup_db.txt'), 'w') as f:
        f.write('')

    # Add an expired file to the file queue storage associated with non-expired account (for test_cleanup_database)
    with open(os.path.join(SUBSCRIBER_QUEUE, 'test_cleanup_db_2.txt'), 'w') as f:
        f.write('')

    # for test_reporting
    data_to_insert.append({
        'username': 'test_account',
        'fileid': 67890,
        'entry_date': datetime.datetime.today(),
        'expires': datetime.datetime.today() + datetime.timedelta(days=1)
    })

    insert_data('file_queue', data_to_insert)


def _add_transactions_entries():
    """Add necessary ``transactions`` table entries used for testing"""

    # Add a transaction (for test_reporting)
    data_to_insert = [{
        'transactionid': 999,
        'action': 'GET /files/666',
        'username': 'test_account',
        'start_time': datetime.datetime.now(),
        'fileid': 67890,
        'source': '/some/starting/location/',
        'destination': '/some/ending/location',
        'end_time': datetime.datetime.now() + datetime.timedelta(hours=1),
        'complete': True
    }]

    insert_data('transactions', data_to_insert)


@pytest.fixture(scope="session", autouse=True)
def setup(request):
    """Setup function"""

    # Remove any data that already exists in the database
    session.query(FileQueue).delete()
    session.query(Transactions).delete()
    session.query(Accounts).delete()
    session.query(FileMetadata).delete()
    session.commit()

    # Add entries to database tables to support tests
    _add_accounts_entries()
    _add_file_metadata_entries()
    _add_file_queue_entries()
    _add_transactions_entries()

    # Run teardown function after all is done
    request.addfinalizer(teardown)


def teardown():
    """Teardown function"""

    # Clean out the database
    session.query(FileQueue).delete()
    session.query(Transactions).delete()
    session.query(Accounts).delete()
    session.query(FileMetadata).delete()
    session.commit()
