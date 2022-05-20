"""
This module contains various functions to remove expired accounts and files
from the database and file queue

Authors
-------
    - Matthew Bourque

Use
---

    This module is intended to be executed via the command line as such:
    ::
        python cleanup_database.py
"""

import datetime
import os

from lasp_sdtp.config import admin_config
from lasp_sdtp.database.database_interface import Accounts
from lasp_sdtp.database.database_interface import FileMetadata
from lasp_sdtp.database.database_interface import FileQueue
from lasp_sdtp.database.database_interface import session


def cleanup_accounts():
    """Removes expired accounts"""

    # Identify any expired accounts
    today = datetime.datetime.today()
    expired_accounts = session.query(Accounts.username).filter(Accounts.registration_expires <= today).all()
    expired_accounts = [item[0] for item in expired_accounts]

    for expired_account in expired_accounts:

        # Remove any files in the queue related to the account
        session.query(FileQueue).filter(FileQueue.username == expired_account).delete()
        session.commit()

        # Remove the expired account
        session.query(Accounts).filter(Accounts.username == expired_account).delete()
        session.commit()


def cleanup_file_queue():
    """Removes expired files from the queue"""

    # Identify any expired files
    today = datetime.datetime.today()
    expired_files = session.query(FileQueue.fileid).filter(FileQueue.expires <= today).all()
    expired_files = [item[0] for item in expired_files]

    for expired_file in expired_files:

        # Remove file from the file queue table
        session.query(FileQueue).filter(FileQueue.fileid == expired_file).delete()
        session.commit()

        # Remove file from the file queue storage
        filename = session.query(FileMetadata.name).filter(FileMetadata.fileid == expired_file).all()
        filename = filename[0][0]
        file_path = os.path.join(admin_config['subscriber_queues_loc'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)


if __name__ == '__main__':

    cleanup_file_queue()
    cleanup_accounts()
