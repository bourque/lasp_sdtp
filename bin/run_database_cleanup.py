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

from pathlib import Path

from lasp_sdtp.database import cleanup
from lasp_sdtp.utils.logging import configure_logging


if __name__ == '__main__':

    # Configure logging
    log_file_loc = Path.home() / 'logs'
    configure_logging(log_file_loc, 'cleanup_database')

    cleanup.cleanup_files()
