"""This module contains functions to remove expired accounts and files from the
database and file queue.

Expired accounts are those for which the current date exceeds the value of the
``accounts.registrationExpires`` database entry.

Expired files are those for which the current date exceeds the value of the
``fileQueue.expires`` database entry.

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

TODO: Make utils function for making a file unavailable
"""

import datetime
import logging
from pathlib import Path

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db

logger = logging.getLogger(__name__)


def cleanup_accounts():
    """Remove expired accounts (and their associated files) from the database
    (and the queue space)"""

    # Identify any expired accounts
    today = datetime.datetime.utcnow().date()
    expired_accounts = db.session.query(db.Accounts.username).filter(db.Accounts.registration_expires <= today).all()
    expired_accounts = [item[0] for item in expired_accounts]

    for expired_account in expired_accounts:

        # Remove any FileQueue table entries related to the account
        db.session.query(db.FileQueue).filter(db.FileQueue.username == expired_account).delete()
        db.session.commit()
        logger.info('Removed FileQueue entries for %s account' % expired_account)

        # Remove any files in the data cache related to the account
        account_cache = Path(admin_config['data_cache_loc']) / expired_account
        account_files = account_cache.glob('*/*')
        for filename in account_files:
            filename.unlink(missing_ok=True)
        logger.info('Removed files from %s queue space' % expired_account)

        # Remove the expired account
        db.session.query(db.Accounts).filter(db.Accounts.username == expired_account).delete()
        db.session.commit()
        logger.info(f'Removed {expired_account} account')


def cleanup_files():
    """Remove expired files from the database and queue space"""

    # Identify any expired files in the Files table
    today = datetime.datetime.utcnow().date()
    expired_files = db.session.query(db.Files.fileid).filter(db.Files.available == True).filter(db.Files.expires <= today).all()
    expired_files = [item[0] for item in expired_files]

    for expired_file in expired_files:

        # Remove file from the FileQueue table
        db.session.query(db.FileQueue).filter(db.FileQueue.fileid == expired_file).delete()
        db.session.commit()
        logger.info(f'Removed file queue database entry for {expired_file}')

        # Update Files table to indicate that the file is no longer available
        db.session.query(db.Files).filter(db.Files.fileid == expired_file).update({'available': False})
        db.session.commit()
        logger.info('Updated Files table to indicate %s is no longer available' % expired_file)

        # Remove file from the file queue storage
        filename = db.session.query(db.Files.name).filter(db.Files.fileid == expired_file).all()
        filename = filename[0][0]
        file_path = Path(admin_config['data_cache_loc']) / subscriber_config['username'] / 'prod' / filename
        file_path.unlink(missing_ok=True)
        logger.info(f'Removed {expired_file} from queue storage')
