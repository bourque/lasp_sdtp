"""Tests for ``cleanup_database.py``

Authors
-------
    Matthew Bourque

Use
---
    pytest test_cleanup_database.py
"""

import datetime
import os

from sqlalchemy import Table

from lasp_sdtp.database.cleanup_database import cleanup_accounts
from lasp_sdtp.database.cleanup_database import cleanup_file_queue
from lasp_sdtp.database.database_interface import Accounts
from lasp_sdtp.database.database_interface import base
from lasp_sdtp.database.database_interface import FileMetadata
from lasp_sdtp.database.database_interface import FileQueue
from lasp_sdtp.database.database_interface import session

HOME_DIR = os.path.expanduser('~')
SUBSCRIBER_QUEUE = f'{HOME_DIR}/Desktop/test_queue/'


class TestDatabase():
    """Tests for the ``cleanup_database`` module"""

    def setup(self, test_method):
        """Method for setting up database entries and files for use in testing"""

        # Set some useful attributes
        self.acc_username = 'test_account'
        self.fq_username = 'test_account2'
        self.test_filename = 'test_file.txt'
        self.fileid = 9999

        # Add an accounts entry that has expired
        table = Table('accounts', base.metadata)
        data_to_insert = [{
            'username': self.acc_username,
            'certuid': 'test_cert',
            'role': 'subscriber',
            'registration_date': datetime.datetime.today(),
            'registration_expires': datetime.datetime.today() - datetime.timedelta(days=1)
        }]
        table.insert().execute(data_to_insert)

        # Add an accounts entry that hasnt expired, for the file_queue test
        table = Table('accounts', base.metadata)
        data_to_insert = [{
            'username': self.fq_username,
            'certuid': 'test_cert2',
            'role': 'subscriber',
            'registration_date': datetime.datetime.today(),
            'registration_expires': datetime.datetime.today() + datetime.timedelta(days=10)
        }]
        table.insert().execute(data_to_insert)

        # Add a file metadata entry for file to satisfy foreign key constraint
        table = Table('file_metadata', base.metadata)
        data_to_insert = [{
            'fileid': self.fileid,
            'name': self.test_filename,
            'checksum': 'abcdefg',
            'size': 1,
            'expires': datetime.datetime.today() + datetime.timedelta(days=1),
            'stream': 'prod',
            'shortname': 'TEST_FILE',
            'version': 'v01'
        }]
        table.insert().execute(data_to_insert)

        # Add a file queue entry for the expired account
        table = Table('file_queue', base.metadata)
        data_to_insert = [{
            'username': self.acc_username,
            'fileid': self.fileid,
            'entry_date': datetime.datetime.today(),
            'expires': datetime.datetime.today() + datetime.timedelta(days=10)  # The file in the queue doesn't necessarily have to be expired
        }]
        table.insert().execute(data_to_insert)

        # Add a file queue entry that is itself expired
        data_to_insert = [{
            'username': self.fq_username,
            'fileid': self.fileid,
            'entry_date': datetime.datetime.today(),
            'expires': datetime.datetime.today() - datetime.timedelta(days=10)
        }]
        table.insert().execute(data_to_insert)

        # Add an expired file to the file queue storage
        with open(os.path.join(SUBSCRIBER_QUEUE, self.test_filename), 'w') as f:
            f.write('')

    def test_cleanup_accounts(self):
        """Tests the ``cleanup_accounts`` function"""

        # Perform cleanup
        cleanup_accounts()

        # Check that there are no expired accounts
        results = session.query(Accounts).filter(Accounts.registration_expires <= datetime.datetime.today()).all()
        assert len(results) == 0

        # Check that there are no files in the queue associated with expired accounts
        results = session.query(FileQueue).filter(FileQueue.username == self.acc_username).all()
        assert len(results) == 0

    def test_cleanup_file_queue(self):
        """Tests the ``cleanup_file_queue`` function"""

        # Perform cleanup
        cleanup_file_queue()

        # Check that there are no expired files in the file queue
        results = session.query(FileQueue.fileid).filter(FileQueue.expires <= datetime.datetime.today()).all()
        assert len(results) == 0

        # Check that the expired file was removed from the queue storage
        assert not os.path.exists(os.path.join(SUBSCRIBER_QUEUE, self.test_filename))

    def teardown(self, test_method):
        """Method for removing database entries and files that were used for
        testing"""

        # Remove entries that were added
        session.query(FileQueue).filter(FileQueue.fileid == self.fileid).delete()
        session.commit()
        session.query(FileMetadata).filter(FileMetadata.fileid == self.fileid).delete()
        session.commit()
        session.query(Accounts).filter(Accounts.username == self.acc_username).delete()
        session.commit()
        session.query(Accounts).filter(Accounts.username == self.fq_username).delete()
        session.commit()
