"""This script creates a directory with (mostly empty) files for testing
purposes.

For each TSIS data product type, files are created for five different days and
are placed in the ``filesystem_loc`` as defined in the ``admin_config.json``
file. The contents of each file only contain one line of text containing the
filename.

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be executed via the command line as such:
    ::
        python create_test_filesystem.py
"""

import datetime
from pathlib import Path

from lasp_sdtp.config import admin_config
from lasp_sdtp.utils.properties import TSIS_FILE_SIZES
from lasp_sdtp.utils.properties import TSIS_FILENAME_STRUCTURES


def create_test_filesystem():
    """Create a small, local filesystem of files used for testing purposes.

    The filesystem is stored in the directory defined by the ``filesystem_loc``
    key in the ``admin_config.json`` file.
    """

    # Create parent directory for storing test files
    test_directory = Path(admin_config['filesystem_loc'])
    test_directory.mkdir(parents=True, exist_ok=True)

    for shortname in TSIS_FILENAME_STRUCTURES:

        # Create files for five different days
        dates = ['20220101', '20220102', '20220103', '20220104', '20220105']
        for date in dates:
            base_filename = TSIS_FILENAME_STRUCTURES[shortname]
            base_filename = base_filename.replace('<date>', date)
            if '<date2>' in base_filename:
                next_day = datetime.datetime.strftime(datetime.datetime.strptime(date, '%Y%m%d') + datetime.timedelta(days=1), '%Y%m%d')
                base_filename = base_filename.replace('<date2>', next_day)

            filename = test_directory / base_filename
            file_contents = f'File contents\n\n'
            file_size = round((TSIS_FILE_SIZES[shortname] * 1e6))
            file_size = round(file_size, -3) - 15  # File header is 15 bytes
            file_contents += '.' * file_size  # Inflate the file to mimic expected sizes
            with open(filename, 'w') as f:
                f.write(file_contents)
            print(f'Created test file: {filename}')


if __name__ == '__main__':

    create_test_filesystem()
