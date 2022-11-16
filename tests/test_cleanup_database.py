"""Tests for then ``cleanup_database.py`` module.

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
from lasp_sdtp.database.cleanup_database import cleanup_files
from lasp_sdtp.database.database_controller import db


def test_cleanup_accounts():
    """Tests the ``cleanup_accounts`` function"""

    # Perform the cleanup
    cleanup_accounts()

    # Check that there are no expired accounts
    results = db.session.query(db.Accounts).filter(db.Accounts.registration_expires <= datetime.datetime.utcnow().date()).all()
    assert len(results) == 0

    # Check that there are no FileQueue entries associated with the expired accounts
    results = db.session.query(db.FileQueue).filter(db.FileQueue.username == 'expired_account').all()
    assert len(results) == 0

    # Check that there are no files in the queue associated with expired accounts
    queue_space = Path(admin_config['data_cache_loc']) / 'expired_account'
    files = list(queue_space.glob('*/*'))
    assert len(files) == 0


def test_cleanup_files():
    """Tests the ``cleanup_files`` function"""

    # Perform the cleanup
    cleanup_files()

    # Check that there are no expired files in the file queue
    results = db.session.query(db.FileQueue.fileid).filter(db.FileQueue.expires <= datetime.datetime.utcnow().date()).all()
    assert len(results) == 0

    # Check that the expired file was removed from the queue storage
    filepath = Path(admin_config['data_cache_loc']) / subscriber_config['username'] / 'prod' / 'test_cleanup_db2.txt'
    assert not filepath.exists()
