"""This script creates a directory with files for testing purposes.

For each TSIS2 data product type, files are created for five different days and
are placed in the ``filesystem_loc`` as defined in the ``admin_config.json``
file. The contents of each file only contain one line of text containing the
filename.

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be executed via the command line as such:
        python create_test_filesystem.py
"""

from lasp_sdtp.utils.utils import create_test_filesystem


if __name__ == '__main__':

    create_test_filesystem()
