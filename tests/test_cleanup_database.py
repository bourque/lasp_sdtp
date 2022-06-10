"""Tests for then ``cleanup_database.py`` module

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_cleanup_database.py
"""

import datetime
from pathlib import Path

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.cleanup_database import cleanup_accounts
from lasp_sdtp.database.cleanup_database import cleanup_file_queue
from lasp_sdtp.database.database_controller import db


def test_cleanup_accounts():
    """Tests the ``cleanup_accounts`` function"""

    # Perform the cleanup
    cleanup_accounts()

    # Check that there are no expired accounts
    results = db.session.query(db.Accounts).filter(db.Accounts.registration_expires <= datetime.datetime.utcnow().date()).all()
    assert len(results) == 0

    # Check that there are no files in the queue associated with expired accounts
    results = db.session.query(db.FileQueue).filter(db.FileQueue.username == 'expired_account').all()
    assert len(results) == 0


def test_cleanup_file_queue():
    """Tests the ``cleanup_file_queue`` function"""

    # Perform the cleanup
    cleanup_file_queue()

    # Check that there are no expired files in the file queue
    results = db.session.query(db.FileQueue.fileid).filter(db.FileQueue.expires <= datetime.datetime.utcnow().date()).all()
    assert len(results) == 0

    # Check that the expired file was removed from the queue storage
    filepath = Path(admin_config['data_cache_loc']) / subscriber_config['username'] / 'test_cleanup_db_2.txt'
    assert not filepath.exists()
