"""This script runs an operation to 'cleanup' the database, removing expired
files and/or accounts.

Authors
-------
    - Matthew Bourque

Use
---

    This module is intended to be executed via the command line as such:
    ::
        python run_cleanup_database.py
"""

from lasp_sdtp.database import cleanup_database


if __name__ == '__main__':

    cleanup_database.cleanup_file_queue()
    cleanup_database.cleanup_accounts()
