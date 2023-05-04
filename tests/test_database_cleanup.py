"""Tests for then ``database.cleanup.py`` module.

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_database_cleanup.py
"""

import datetime
from pathlib import Path

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.cleanup import cleanup_files
from lasp_sdtp.database.controller import db


def test_cleanup_files():
    """Tests the ``cleanup_files`` function"""

    # Perform the cleanup
    cleanup_files()

    # Check that there are no expired files in the file queue
    results = db.session.query(
                  db.FileQueue.fileid
              ).filter(
                  db.FileQueue.expires <= datetime.datetime.utcnow().date()
              ).all()
    assert len(results) == 0

    # Check that the expired file was removed from the subscriber queue staging area
    filepath = Path(admin_config['staging_loc']) / subscriber_config['username'] / 'prod' / 'test_cleanup_db2.txt'
    assert not filepath.exists()
