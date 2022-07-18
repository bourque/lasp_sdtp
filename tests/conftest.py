"""This module contains code to perform the setup and teardown necessary to
run the test suite contained within the ``tests`` directory.

Authors
-------
    Matthew Bourque

Use
---
    This module gets automatically executed before any tests when using
    ``pytest -s .`` or ``pytest -s <module>``
"""

import datetime
import glob
import os
from pathlib import Path

import pytest

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db
from lasp_sdtp.utils import utils


def _add_accounts_entries():
    """Add necessary ``accounts`` table entries used for testing"""

    # Add nominal test account used for general testing
    data_to_insert = [{
        'username': 'test_account',
        'certuid': 'test_cert',
        'role': 'subscriber',
        'registration_date': datetime.datetime.utcnow().date(),
        'registration_expires': datetime.datetime.utcnow().date() + datetime.timedelta(days=1)}]

    # Add an account for the subscriber (used for test_database_interface)
    data_to_insert.append({
        'username': subscriber_config['username'],
        'certuid': 'test_cert',
        'role': 'subscriber',
        'registration_date': datetime.datetime.utcnow().date(),
        'registration_expires': datetime.datetime.utcnow().date() + datetime.timedelta(days=1)}
    )

    # Add an account that has expired (used for test_cleanup_database)
    data_to_insert.append({
        'username': 'expired_account',
        'certuid': 'test_cert',
        'role': 'subscriber',
        'registration_date': datetime.datetime.utcnow().date(),
        'registration_expires': datetime.datetime.utcnow().date() - datetime.timedelta(days=1)}
    )

    db.insert_data('accounts', data_to_insert)


def _add_file_metadata_entries():
    """Add necessary ``file_metadata`` table entries used for testing"""

    # Locate files in test filesystem
    test_files = glob.glob(str(Path(admin_config['filesystem_loc']) / '*'))

    # Insert test file data (mostly used for test_run_server)
    data_to_insert = []
    for i, test_file in enumerate(test_files):
        data = {
            'name': Path(test_file).name,
            'checksum': utils.get_checksum(),
            'size': os.path.getsize(test_file),
            'expires': datetime.datetime.utcnow().date() + datetime.timedelta(days=subscriber_config['expiration_period']),
            'stream': 'prod',
            'shortname': utils.get_shortname(Path(test_file).name),
            'version': 'v01',
            'date': datetime.datetime(2022, 1, 1).date() + datetime.timedelta(days=i - 1)
        }
        data_to_insert.append(data)
    db.insert_data('file_metadata', data_to_insert)

    # Add entries to satisfy integrity constraint for test_cleanup_database
    data_to_insert = [{
        'fileid': 12345,
        'name': 'test_cleanup_db.txt',
        'checksum': 'foo',
        'size': 1,
        'expires': datetime.datetime.utcnow().date() + datetime.timedelta(days=1),
        'stream': 'prod',
        'shortname': 'TEST_FILE',
        'version': 'v01',
        'date': datetime.datetime(2022, 1, 1).date()
    }]
    data_to_insert.append({
        'fileid': 12346,
        'name': 'test_cleanup_db2.txt',
        'checksum': 'bar',
        'size': 1,
        'expires': datetime.datetime.utcnow().date() + datetime.timedelta(days=1),
        'stream': 'prod',
        'shortname': 'TEST_FILE',
        'version': 'v01',
        'date': datetime.datetime(2022, 1, 1).date()
    })

    # Add entry to satisfy integrity constraint for test_reporting
    data_to_insert.append({
        'fileid': 67890,
        'name': 'test_reporting.txt',
        'checksum': 'bop',
        'size': 1,
        'expires': datetime.datetime.utcnow().date() + datetime.timedelta(days=1),
        'stream': 'prod',
        'shortname': 'TEST_FILE',
        'version': 'v01',
        'date': datetime.datetime(2022, 1, 1).date()
    })

    # Add entry to satisfy integrity constraint for test_database_controller
    data_to_insert.append({
        'fileid': 78901,
        'name': 'test_db_controller.txt',
        'checksum': 'bat',
        'size': 1,
        'expires': datetime.datetime.utcnow().date() + datetime.timedelta(days=1),
        'stream': 'prod',
        'shortname': 'TEST_FILE',
        'version': 'v01',
        'date': datetime.datetime(2022, 1, 1).date()
    })

    # A seperate call to insert_data() is needed so that the correct fileids are inserted
    db.insert_data('file_metadata', data_to_insert)


def _add_file_queue_entries():
    """Add necessary ``file_queue`` table entries used for testing"""

    # Add an entry associated with the expired account (for test_cleanup_database)
    data_to_insert = [{
        'username': 'expired_account',
        'fileid': 12345,
        'entry_date': datetime.datetime.utcnow().date(),
        'expires': datetime.datetime.utcnow().date() - datetime.timedelta(days=10)
    }]

    # Add an entry not associated with the expired account (for test_cleanup_database)
    data_to_insert.append({
        'username': 'test_account',
        'fileid': 12346,
        'entry_date': datetime.datetime.utcnow().date(),
        'expires': datetime.datetime.utcnow().date() - datetime.timedelta(days=10)
    })

    # Add an expired file to the file queue storage associated with expired account (for test_cleanup_database)
    with open(Path(admin_config['data_cache_loc']) / 'test_cleanup_db.txt', 'w') as f:
        f.write('')

    # Add an expired file to the file queue storage associated with non-expired account (for test_cleanup_database)
    with open(Path(admin_config['data_cache_loc']) / 'test_cleanup_db_2.txt', 'w') as f:
        f.write('')

    # Add an entry used for test_reporting
    data_to_insert.append({
        'username': 'test_account',
        'fileid': 67890,
        'entry_date': datetime.datetime.utcnow().date(),
        'expires': datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
    })

    # Add an entry used for test_database_controller
    data_to_insert.append({
        'username': 'test_account',
        'fileid': 78901,
        'entry_date': datetime.datetime.utcnow().date(),
        'expires': datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
    })

    db.insert_data('file_queue', data_to_insert)


def _add_transactions_entries():
    """Add necessary ``transactions`` table entries used for testing"""

    # Add a transaction for test_reporting
    data_to_insert = [{
        'transactionid': 999,
        'action': 'GET /files/666',
        'username': 'test_account',
        'start_time': datetime.datetime.utcnow() - datetime.timedelta(hours=36),  # A "long" transfer
        'fileid': 67890,
        'source': '/some/starting/location/',
        'destination': '/some/ending/location',
        'end_time': None,
    }]

    db.insert_data('transactions', data_to_insert)


@pytest.fixture(scope="session", autouse=True)
def setup(request):
    """Setup function"""

    # Remove any data that may already exist in the database
    db.session.query(db.FileQueue).delete()
    db.session.query(db.Transactions).delete()
    db.session.query(db.Accounts).delete()
    db.session.query(db.FileMetadata).delete()
    db.session.commit()

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
    db.session.query(db.FileQueue).delete()
    db.session.query(db.Transactions).delete()
    db.session.query(db.Accounts).delete()
    db.session.query(db.FileMetadata).delete()
    db.session.commit()
