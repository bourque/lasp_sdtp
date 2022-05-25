"""Inserts the same testing data used in ``conftest.py``, only the user can
trigger it manually via the command line.  This is handy if users wish to test
the application with ``curl`` commands in the terminal

Authors
-------
    Matthew Bourque

Use
---
    This modules is intended to be run via the command line as such:
    ::
        python insert_test_eata.py
"""

from lasp_sdtp.database.database_interface import Accounts
from lasp_sdtp.database.database_interface import FileMetadata
from lasp_sdtp.database.database_interface import FileQueue
from lasp_sdtp.database.database_interface import session
from lasp_sdtp.database.database_interface import Transactions

from conftest import _add_accounts_entries
from conftest import _add_file_metadata_entries
from conftest import _add_file_queue_entries
from conftest import _add_transactions_entries


if __name__ == '__main__':

    # Remove any data that may already exist in the database
    session.query(FileQueue).delete()
    session.query(Transactions).delete()
    session.query(Accounts).delete()
    session.query(FileMetadata).delete()
    session.commit()

    # Add entries to database tables to support tests
    _add_accounts_entries()
    _add_file_metadata_entries()
    _add_file_queue_entries()
    _add_transactions_entries()
