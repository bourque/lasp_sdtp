"""This script ingests TSIS2 data into the database.

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be executed via the command line as such:
    ::
        python ingest_tsis2_data.py

TODO: Add support for ingesting data from dropbox folder
"""

import glob
from pathlib import Path

from lasp_sdtp.config import admin_config
from lasp_sdtp.database.ingest import Ingest

if __name__ == '__main__':

    # Read in filesystem
    # Currently these files are read directly from a test filesystem, but this
    # Could be modified to listen to a dropbox folder, for example
    filelist = glob.glob(str(Path(admin_config['filesystem_loc']) / 'prod' / '*'))

    # Ingest a 'production' stream of the data
    production = Ingest(filelist, 'prod', '01')
    production.ingest()

    # Ingest a 'development' stream of the data
    development = Ingest(filelist, 'dev', '01')
    development.ingest()
