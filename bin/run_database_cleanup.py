"""This script runs an operation to 'cleanup' the database, removing expired
files and/or accounts.

Authors
-------
    - Matthew Bourque

Use
---

    This module is intended to be executed via the command line as such:
    ::
        python run_database_cleanup.py
"""

from lasp_sdtp.database import cleanup


if __name__ == '__main__':

    cleanup.cleanup_files()
