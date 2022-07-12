"""This module contains functions to remove expired accounts and files from the
database and file queue.

Authors
-------
    - Matthew Bourque

Use
---

    This module is intended to be imported and used by
    ``bin/run_cleanup_database.py``:
    ::
        from lasp_sdtp.database import cleanup_database
        cleanup_database.cleanup_accounts()
"""

import datetime
from pathlib import Path

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db


def cleanup_accounts():
    """Remove expired accounts"""

    # Identify any expired accounts
    today = datetime.datetime.utcnow().date()
    expired_accounts = db.session.query(db.Accounts.username).filter(db.Accounts.registration_expires <= today).all()
    expired_accounts = [item[0] for item in expired_accounts]

    for expired_account in expired_accounts:

        # Remove any files in the queue related to the account
        db.session.query(db.FileQueue).filter(db.FileQueue.username == expired_account).delete()
        db.session.commit()

        # Remove the expired account
        db.session.query(db.Accounts).filter(db.Accounts.username == expired_account).delete()
        db.session.commit()


def cleanup_file_queue():
    """Remove expired files from the ``file_queue`` database table and data
    cache"""

    # Identify any expired files
    today = datetime.datetime.utcnow().date()
    expired_files = db.session.query(db.FileQueue.fileid).filter(db.FileQueue.expires <= today).all()
    expired_files = [item[0] for item in expired_files]

    for expired_file in expired_files:

        # Remove file from the file queue table
        db.session.query(db.FileQueue).filter(db.FileQueue.fileid == expired_file).delete()
        db.session.commit()

        # Remove file from the file queue storage
        filename = db.session.query(db.FileMetadata.name).filter(db.FileMetadata.fileid == expired_file).all()
        filename = filename[0][0]
        file_path = Path(admin_config['data_cache_loc']) / subscriber_config['username'] / filename
        file_path.unlink(missing_ok=True)
