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

from lasp_sdtp.database.cleanup_database import cleanup_accounts
from lasp_sdtp.database.cleanup_database import cleanup_file_queue
from lasp_sdtp.database.database_interface import Accounts
from lasp_sdtp.database.database_interface import FileQueue
from lasp_sdtp.database.database_interface import session

HOME_DIR = os.path.expanduser('~')
SUBSCRIBER_QUEUE = f'{HOME_DIR}/Desktop/test_queue/'


def test_cleanup_accounts():
    """Tests the ``cleanup_accounts`` function"""

    # Perform cleanup
    cleanup_accounts()

    # Check that there are no expired accounts
    results = session.query(Accounts).filter(Accounts.registration_expires <= datetime.datetime.today()).all()
    assert len(results) == 0

    # Check that there are no files in the queue associated with expired accounts
    results = session.query(FileQueue).filter(FileQueue.username == 'expired_account').all()
    assert len(results) == 0


def test_cleanup_file_queue():
    """Tests the ``cleanup_file_queue`` function"""

    # Perform cleanup
    cleanup_file_queue()

    # Check that there are no expired files in the file queue
    results = session.query(FileQueue.fileid).filter(FileQueue.expires <= datetime.datetime.today()).all()
    assert len(results) == 0

    # Check that the expired file was removed from the queue storage
    assert not os.path.exists(os.path.join(SUBSCRIBER_QUEUE, 'test_cleanup_db_2.txt'))
