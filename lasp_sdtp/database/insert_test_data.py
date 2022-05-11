"""
This module contains various functions to insert data into the database for
testing purposes

Authors
-------
    - Matthew Bourque

Use
---

    This module is intended to be imported and used within other modules, e.g.:
    ::
        from lasp_sdtp.database.insert_test_data import insert_test_data
"""

import datetime
import glob
import os
import random
import string

from sqlalchemy import Table

from lasp_sdtp.config import config
from lasp_sdtp.database.database_interface import Accounts
from lasp_sdtp.database.database_interface import base
from lasp_sdtp.database.database_interface import FileMetadata
from lasp_sdtp.database.database_interface import FileQueue
from lasp_sdtp.database.database_interface import session
from lasp_sdtp.database.database_interface import Transactions


HOME_DIR = os.path.expanduser('~')
FILESYSTEM_PATH = f'{HOME_DIR}/Desktop/test_filesystem/'
SUBSCRIBER_QUEUE = f'{HOME_DIR}/Desktop/test_queue/'


def _get_checksum():
    """Return a randomly generated checksum

    Returns
    -------
    checksum : str
        A randomly generated checksum based on the ``checksum_type`` given in
        the system configuration
    """

    checksum_type = config['checksum_type']
    checksum_string = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(64))
    checksum = f'{checksum_type}:{checksum_string}'

    return checksum


def _get_shortname(filename):
    """Return the appropriate ``ShortName`` for the given filename.

    Parameters
    ----------
    filename : str
        The filename of interest (e.g. ``tsis2_tim_L2_v01_20220422.zip``)

    Returns
    -------
    shortname : str
        The ``ShortName`` that matches the given filename (e.g. ``TSIS2_TIM_L2``)
    """

    shortname_mapping = {
        'tsis2_L1': 'TSIS2_L1',
        'tsis2_sim_cal': 'TSIS2_SIM_CAL',
        'tsis2_tim_cal': 'TSIS2_TIM_CAL',
        'tsis2_sim_L2': 'TSIS2_SIM_L2',
        'tsis2_tim_L2': 'TSIS2_TIM_L2',
        'tsis2_sc_L2': 'TSIS_SC_L2',
        'tsis2_ssi_L3_c12h': 'TSIS2_SSI_L3_12HR',
        'tsis2_ssi_L3_c24h': 'TSIS2_SSI_L3_24HR',
        'tsis2_tsi_L3_c06h': 'TSIS2_TSI_L3_06HR',
        'tsis2_tsi_L3_c24h': 'TSIS2_TSI_L3_24HR'
    }

    for item in shortname_mapping:
        if filename.startswith(item):
            shortname = shortname_mapping[item]
            if filename.endswith('.txt'):
                shortname += '_TXT'
            elif filename.endswith('.nc'):
                shortname += '_NC'

    return shortname


def insert_test_data():
    """Insert test data into the test database. The data that are insterted is
    based on which files exist in the ``test_filesystem``
    """

    # Remove any data that already exists
    session.query(FileQueue).delete()
    session.query(Transactions).delete()
    session.query(Accounts).delete()
    session.query(FileMetadata).delete()
    session.commit()

    table = Table('file_metadata', base.metadata)

    # Locate test files
    test_filesystem = f'{HOME_DIR}/Desktop/test_filesystem/'
    test_files = glob.glob(os.path.join(test_filesystem, '*'))

    # Gather metadata to store in database
    data_to_insert = []
    for i, test_file in enumerate(test_files):
        data = {
            'name': os.path.basename(test_file),
            'checksum': _get_checksum(),
            'size': os.path.getsize(test_file),
            'expires': datetime.datetime.today() + datetime.timedelta(days=config['expiration_period']),
            'stream': 'prod',
            'shortname': _get_shortname(os.path.basename(test_file)),
            'version': 'v01'
        }
        data_to_insert.append(data)

    # Insert data into database
    table.insert().execute(data_to_insert)
