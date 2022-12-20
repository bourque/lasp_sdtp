"""This script inserts the same testing data that is defined in ``conftest.py``
into the database.  This is handy if developers wish to test the application
with ``curl`` commands in the terminal and need a basic set of test data
available in the database.

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be run via the command line as such:
    ::
        python insert_test_data.py
"""

from lasp_sdtp.database.database_controller import db

from tests import conftest

if __name__ == '__main__':

    # Remove any data that may already exist in the database
    db.session.query(db.FileQueue).delete()
    db.session.query(db.Transactions).delete()
    db.session.query(db.TagsAndExtras).delete()
    db.session.query(db.Files).delete()
    db.session.query(db.MissionShortnameMapping).delete()
    db.session.query(db.Shortnames).delete()
    db.session.query(db.MissionAccountMapping).delete()
    db.session.query(db.Missions).delete()
    db.session.query(db.Accounts).delete()
    db.session.commit()

    # Add entries to database tables to support tests
    conftest._add_missions_entries()
    conftest._add_accounts_entries()
    conftest._add_mission_account_mapping_entries()
    conftest._add_shortnames_entries()
    conftest._add_mission_shortname_mapping_entries()
    conftest._add_files_entries()
    conftest._add_file_queue_entries()
    conftest._add_transactions_entries()
