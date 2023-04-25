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

    The functions within are also used by
    ``server.ancillary.remove_expired_data`` to invoke cleanup before every
    API request to ensure there is no access to expired data
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

        # Remove any files in the subscriber queue staging area related to the account
        account_cache = Path(admin_config['staging_loc']) / expired_account
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
    expired_files = db.session.query(
                        db.Files.fileid
                    ).filter(
                        db.Files.available == True,
                        db.Files.expires <= today
                    ).all()
    expired_files = [item[0] for item in expired_files]

    for expired_file in expired_files:

        # Remove file from the FileQueue table
        db.session.query(db.FileQueue).filter(db.FileQueue.fileid == expired_file).delete()
        db.session.commit()
        logger.info(f'Removed file queue database entry for {expired_file}')

        # Update Files table to indicate that the file is no longer available
        db.mark_as_deleted(expired_file)

        # Remove file from the file queue staging area
        filename = db.session.query(db.Files.name).filter(db.Files.fileid == expired_file).one()
        filename = filename[0]
        file_path = Path(admin_config['staging_loc']) / subscriber_config['username'] / 'prod' / filename
        file_path.unlink(missing_ok=True)
        logger.info(f'Removed {expired_file} from subscriber queue staging area')
