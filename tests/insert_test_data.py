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

from lasp_sdtp.database.database_controller import db

import conftest

if __name__ == '__main__':

    # Remove any data that may already exist in the database
    db.session.query(db.FileQueue).delete()
    db.session.query(db.Transactions).delete()
    db.session.query(db.Accounts).delete()
    db.session.query(db.FileMetadata).delete()
    db.session.commit()

    # Add entries to database tables to support tests
    conftest._add_accounts_entries()
    conftest._add_file_metadata_entries()
    conftest._add_file_queue_entries()
    conftest._add_transactions_entries()
