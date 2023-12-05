"""This script ingests TSIS data into the database.

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be executed via the command line as such:
    ::
        python ingest_tsis_data.py
"""

import glob
from pathlib import Path

from lasp_sdtp.config import admin_config
from lasp_sdtp.database.ingest import Ingest

if __name__ == '__main__':

    # Read in filesystem
    filelist = glob.glob(str(Path(admin_config['filesystem_loc']) / '*'))

    # Ingest a 'production' stream of the data
    production = Ingest(filelist, 'prod', '01')
    production.ingest()

    # Ingest a 'development' stream of the data
    development = Ingest(filelist, 'dev', '01')
    development.ingest()
