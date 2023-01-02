"""This module contains code to perform the setup and teardown necessary to
run the test suite contained within the ``tests`` directory.

A number of entries are inserted into to the database tables in order to support
the unit tests via the ``setup`` function.  Upon completion of running
``pytest``, the database is cleared out via the ``teardown`` function.

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
import shutil
from pathlib import Path

import pytest

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db
from lasp_sdtp.utils import utils

TEST_SHORTNAME_MAPPING = {
    'TSIS2_L1': r'tsis2_L1_(?P<date>\d{8}).zip',
    'TSIS2_SIM_CAL': r'tsis2_sim_cal_v(?P<version>\d{2}).zip',
    'TSIS2_TIM_CAL': r'tsis2_tim_cal_v(?P<version>\d{2}).zip',
    'TSIS2_SIM_L2': r'tsis2_sim_L2_v(?P<version>\d{2})_(?P<date>\d{8}).zip',
    'TSIS2_TIM_L2': r'tsis2_tim_L2_v(?P<version>\d{2})_(?P<date>\d{8}).zip',
    'TSIS2_SC_L2': r'tsis2_sc_L2_v(?P<version>\d{2})_(?P<start_date>\d{8})_(?P<end_date>\d{8}).zip',
    'TSIS2_SSI_L3_12HR_TXT': r'tsis2_ssi_L3_c12h_v(?P<version>\d{2})_(?P<start_date>\d{8})_(?P<end_date>\d{8}).txt',
    'TSIS2_SSI_L3_24HR_TXT': r'tsis2_ssi_L3_c24h_v(?P<version>\d{2})_(?P<start_date>\d{8})_(?P<end_date>\d{8}).txt',
    'TSIS2_TSI_L3_06HR_TXT': r'tsis2_tsi_L3_c06h_v(?P<version>\d{2})_(?P<start_date>\d{8})_(?P<end_date>\d{8}).txt',
    'TSIS2_TSI_L3_24HR_TXT': r'tsis2_tsi_L3_c24h_v(?P<version>\d{2})_(?P<start_date>\d{8})_(?P<end_date>\d{8}).txt',
    'TSIS2_SSI_L3_12HR_NC': r'tsis2_ssi_L3_c12h_v(?P<version>\d{2})_(?P<start_date>\d{8})_(?P<end_date>\d{8}).nc',
    'TSIS2_SSI_L3_24HR_NC': r'tsis2_ssi_L3_c24h_v(?P<version>\d{2})_(?P<start_date>\d{8})_(?P<end_date>\d{8}).nc',
    'TSIS2_TSI_L3_06HR_NC': r'tsis2_tsi_L3_c06h_v(?P<version>\d{2})_(?P<start_date>\d{8})_(?P<end_date>\d{8}).nc',
    'TSIS2_TSI_L3_24HR_NC': r'tsis2_tsi_L3_c24h_v(?P<version>\d{2})_(?P<start_date>\d{8})_(?P<end_date>\d{8}).nc'
}


def _add_accounts_entries():
    """Add ``Accounts`` table entries used for testing"""

    # Add nominal test account used for general testing
    data_to_insert = [db.Accounts(
        username='test_account',
        role='subscriber',
        registration_open=True,
        certuid='test_cert',
    )]

    # Add an account for the subscriber
    data_to_insert.append(db.Accounts(
        username='ges_disc',
        role='subscriber',
        registration_open=True,
        certuid='test_cert'
    ))

    # Add an account that has expired (used for test_cleanup_database)
    data_to_insert.append(db.Accounts(
        username='expired_account',
        role='subscriber',
        registration_open=False,
        certuid='test_cert',
        registration_date=datetime.datetime.utcnow().date(),
        registration_expires=datetime.datetime.utcnow().date() - datetime.timedelta(days=1)
    ))

    # Add an account that has not yet registered but has registration window closed
    data_to_insert.append(db.Accounts(
        username='not_open_for_registration',
        role='subscriber',
        registration_open=False
    ))

    db.insert_data(data_to_insert)


def _add_file_queue_entries():
    """Add ``FileQueue`` table entries used for testing"""

    # Add an entry associated with the expired account (for test_cleanup_database)
    data_to_insert = [db.FileQueue(
        username='expired_account',
        fileid=12345,
        entry_date=datetime.datetime.utcnow().date(),
        expires=datetime.datetime.utcnow().date() - datetime.timedelta(days=10)
    )]

    # Add an entry not associated with the expired account (for test_cleanup_database)
    data_to_insert.append(db.FileQueue(
        username='test_account',
        fileid=12346,
        entry_date=datetime.datetime.utcnow().date(),
        expires=datetime.datetime.utcnow().date() - datetime.timedelta(days=10)
    ))

    # Create a queue space for the expired account (used in test_cleanup_database)
    queue_path = Path(admin_config['data_cache_loc']) / 'expired_account' / 'prod'
    queue_path.mkdir(parents=True, exist_ok=True)

    # Add a file associated with expired account (used in test_cleanup_database)
    with open(queue_path / 'test_cleanup_db.txt', 'w') as f:
        f.write('')

    # Add an expired file to the file queue storage associated with non-expired account (for test_cleanup_database)
    with open(Path(admin_config['data_cache_loc']) / 'test_account' / 'prod' / 'test_cleanup_db2.txt', 'w') as f:
        f.write('')

    # Add an entry used for test_reporting
    data_to_insert.append(db.FileQueue(
        username='test_account',
        fileid=67890,
        entry_date=datetime.datetime.utcnow().date(),
        expires=datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
    ))

    # Add an entry used for test_database_controller
    data_to_insert.append(db.FileQueue(
        username='test_account',
        fileid=78901,
        entry_date=datetime.datetime.utcnow().date(),
        expires=datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
    ))

    db.insert_data(data_to_insert)


def _add_files_entries():
    """Add ``Files`` table entries used for testing"""

    # Locate files in test filesystem
    test_files = glob.glob(str(Path(admin_config['filesystem_loc']) / 'prod' / '*'))

    # Create a queue space for the test account
    queue_path = Path(admin_config['data_cache_loc']) / 'test_account' / 'prod'
    queue_path.mkdir(parents=True, exist_ok=True)

    # Copy files to test subscriber queue
    for test_file in test_files:
        dst = queue_path / Path(test_file).name
        shutil.copyfile(test_file, dst)

    # Insert test file data (mostly used for test_run_server)
    data_to_insert = []
    for i, test_file in enumerate(test_files):
        data = db.Files(
            name=Path(test_file).name,
            checksum=utils.get_checksum(),
            size=os.path.getsize(test_file),
            expires=datetime.datetime.utcnow().date() + datetime.timedelta(days=subscriber_config['expiration_period']),
            stream='prod',
            shortname=utils.get_shortname(Path(test_file).name),
            version='01',
            ingest_date=datetime.datetime(2022, 1, 1).date() + datetime.timedelta(days=i - 1),
            available=True,
        )
        data_to_insert.append(data)
    db.insert_data(data_to_insert)

    # Add entries to satisfy integrity constraint for test_cleanup_database
    data_to_insert = [db.Files(
        fileid=12345,
        name='test_cleanup_db.txt',
        checksum='foo',
        size=1,
        expires=datetime.datetime.utcnow().date() + datetime.timedelta(days=1),
        stream='prod',
        shortname='TSIS2_L1',
        version='01',
        ingest_date=datetime.datetime(2022, 1, 1).date(),
        available=True
    )]
    data_to_insert.append(db.Files(
        fileid=12346,
        name='test_cleanup_db2.txt',
        checksum='bar',
        size=1,
        expires=datetime.datetime.utcnow().date() - datetime.timedelta(days=1),
        stream='prod',
        shortname='TSIS2_L1',
        version='01',
        ingest_date=datetime.datetime(2022, 1, 1).date(),
        available=True
    ))

    # Add entry to satisfy integrity constraint for test_reporting
    data_to_insert.append(db.Files(
        fileid=67890,
        name='test_reporting.txt',
        checksum='bop',
        size=1,
        expires=datetime.datetime.utcnow().date() + datetime.timedelta(days=1),
        stream='prod',
        shortname='TSIS2_L1',
        version='01',
        ingest_date=datetime.datetime(2022, 1, 1).date(),
        available=True
    ))

    # Add entry to satisfy integrity constraint for test_database_controller
    data_to_insert.append(db.Files(
        fileid=78901,
        name='test_db_controller.txt',
        checksum='bat',
        size=1,
        expires=datetime.datetime.utcnow().date() + datetime.timedelta(days=1),
        stream='prod',
        shortname='TSIS2_L1',
        version='01',
        ingest_date=datetime.datetime(2022, 1, 1).date(),
        available=True
    ))

    # Add 'restricted' file (used to test utils.validate_access)
    data_to_insert.append(db.Files(
        fileid=23456,
        name='restricted_file.txt',
        checksum='fop',
        size=1,
        expires=datetime.datetime.utcnow().date() + datetime.timedelta(days=1),
        stream='prod',
        shortname='RESTRICTED',
        version='01',
        ingest_date=datetime.datetime.utcnow().date(),
        available=True
    ))

    # A separate call to insert data is needed so that the correct fileids are inserted
    db.insert_data(data_to_insert)


def _add_mission_account_mapping_entries():
    """Add ``MissionAccountMapping`` table entries used for testing"""

    data_to_insert = [db.MissionAccountMapping(
        mission='TSIS2',
        account='test_account'
    )]

    db.insert_data(data_to_insert)


def _add_missions_entries():
    """Add ``Missions`` table entries used for testing"""

    data_to_insert = [db.Missions(
        mission='TSIS2',
        ingest_directory='/path/to/tsis2/data/'
    )]

    # Add 'test' mission (used in test_ingest)
    data_to_insert.append(db.Missions(
        mission='TEST',
        ingest_directory='/path/to/test_data/'
    ))

    db.insert_data(data_to_insert)


def _add_mission_shortname_mapping_entries():
    """Add  ``MissionShortnameMapping`` table entries used for testing"""

    data_to_insert = []

    for shortname in TEST_SHORTNAME_MAPPING:
        data_to_insert.append(db.MissionShortnameMapping(
            mission='TSIS2',
            shortname=shortname
        ))

    # Map the 'TEST_INGEST' shortname to the 'TEST' mission (used in test_ingest)
    data_to_insert.append(db.MissionShortnameMapping(
        mission='TEST',
        shortname='TEST_INGEST'
    ))

    db.insert_data(data_to_insert)


def _add_shortnames_entries():
    """Add ``Shortnames`` table entries used for testing"""

    # Add nominal shortnames
    data_to_insert = [db.Shortnames(shortname=shortname, filename_pattern=TEST_SHORTNAME_MAPPING[shortname]) for shortname in TEST_SHORTNAME_MAPPING]

    # Add 'test' shortname (used in test_ingest)
    data_to_insert.append(db.Shortnames(shortname='TEST_INGEST', filename_pattern='not_subscribed.txt'))

    # Add a 'restricted' shortname (used to test utils.validate_access)
    data_to_insert.append(db.Shortnames(shortname='RESTRICTED', filename_pattern='some_regex_expression'))

    db.insert_data(data_to_insert)


def _add_transactions_entries():
    """Add ``Transactions`` table entries used for testing"""

    # Add a transaction for test_reporting
    data_to_insert = [db.Transactions(
        transactionid=999,
        action='GET /files/666',
        username='test_account',
        start_time=datetime.datetime.utcnow() - datetime.timedelta(hours=36),  # A "long" transfer
        fileid=67890,
        source='/some/starting/location/',
        destination='/some/ending/location',
        end_time=None,
    )]

    db.insert_data(data_to_insert)


@pytest.fixture(scope="session", autouse=True)
def setup(request: object):
    """Setup function"""

    # Remove any data that may already exist in the database
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
    _add_missions_entries()
    _add_accounts_entries()
    _add_mission_account_mapping_entries()
    _add_shortnames_entries()
    _add_mission_shortname_mapping_entries()
    _add_files_entries()
    _add_file_queue_entries()
    _add_transactions_entries()

    # Run teardown function after all is done
    request.addfinalizer(teardown)


def teardown():
    """Teardown function"""
    pass
    # Clean out the database
    # db.session.query(db.FileQueue).delete()
    # db.session.query(db.Transactions).delete()
    # db.session.query(db.TagsAndExtras).delete()
    # db.session.query(db.Files).delete()
    # db.session.query(db.MissionShortnameMapping).delete()
    # db.session.query(db.Shortnames).delete()
    # db.session.query(db.MissionAccountMapping).delete()
    # db.session.query(db.Missions).delete()
    # db.session.query(db.Accounts).delete()
    # db.session.commit()
