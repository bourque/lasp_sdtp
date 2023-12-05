"""This module contains functions to remove expired accounts and files from the
database and file queue.

Expired accounts are those for which the current date exceeds the value of the
``accounts.registrationExpires`` database entry.

Expired files are those for which the current date exceeds the value of the
``fileQueue.expires`` database entry.

Authors
-------
    - Matthew Bourque

Example
-------

    ::
        from lasp_sdtp.database import cleanup
        cleanup.cleanup_files()
"""

import datetime
import logging
from pathlib import Path

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.controller import db

logger = logging.getLogger(__name__)


def cleanup_files():
    """Remove expired files from the database and queue space"""

    logger.info('Removing expired files')

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
        logger.debug('Removed file queue database entry for file %s', expired_file)

        # Update Files table to indicate that the file is no longer available
        db.mark_as_deleted(expired_file)

        # Remove file from the file queue staging area
        filename = db.session.query(db.Files.name).filter(db.Files.fileid == expired_file).one()
        filename = filename[0]
        file_path = Path(admin_config['staging_loc']) / subscriber_config['username'] / 'prod' / filename
        file_path.unlink(missing_ok=True)
        logger.debug('Removed file %s from subscriber queue staging area', expired_file)
