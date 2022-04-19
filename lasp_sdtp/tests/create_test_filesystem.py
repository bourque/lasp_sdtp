"""Creates a directory with files for testing purposes.

For each TSIS2 data product type, files are created for five different days
and are placed in the ``test_filesystem_path``.  The contents of each file only
contain one line of text.

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be used via the command line as such:
        python create_test_filesystem
"""

import datetime
import os

HOME_DIR = os.path.expanduser('~')
TEST_FILESYSTEM_PATH = f'{HOME_DIR}/Desktop/test_filesystem/'


def create_test_filesystem(test_filesystem_path=TEST_FILESYSTEM_PATH):
    """The main function of the module.  See module docstrings for further
    details.

    Parameters
    ----------
    test_filesystem_path : str
        The parent direction in which to create test files
    """

    filename_structures = {
        'TSIS2_L1': 'tsis2_L1_<date>.zip',
        'TSIS2_SIM_CAL': 'tsis2_sim_cal_v01.zip',
        'TSIS2_TIM_CAL': 'tsis2_tim_cal_v01.zip',
        'TSIS2_SIM_L2': 'tsis2_sim_L2_v01_<date>.zip',
        'TSIS2_TIM_L2': 'tsis2_tim_L2_v01_<date>.zip',
        'TSIS2_SC_L2': 'tsis2_sc_L2_v01_<date>_<date2>.zip',
        'TSIS2_SSI_L3_12HR_TXT': 'tsis2_ssi_L3_c12h_v01_<date>_<date2>.txt',
        'TSIS2_SSI_L3_24HR_TXT': 'tsis2_ssi_L3_c24h_v01_<date>_<date2>.txt',
        'TSIS2_TSI_L3_06HR_TXT': 'tsis2_tsi_L3_c06h_v01_<date>_<date2>.txt',
        'TSIS2_TSI_L3_24HR_TXT': 'tsis2_tsi_L3_c24h_v01_<date>_<date2>.txt',
        'TSIS2_SSI_L3_12HR_NC': 'tsis2_ssi_L3_c12h_v01_<date>_<date2>.nc',
        'TSIS2_SSI_L3_24HR_NC': 'tsis2_ssi_L3_c12h_v01_<date>_<date2>.nc',
        'TSIS2_TSI_L3_06HR_NC': 'tsis2_tsi_L3_c06h_v01_<date>_<date2>.nc',
        'TSIS2_TSI_L3_24HR_NC': 'tsis2_tsi_L3_c24h_v01_<date>_<date2>.nc'
    }

    for shortname in filename_structures:

        # Create files for five different days
        dates = ['20220419', '20220420', '20220421', '20220422', '20220423']
        for date in dates:
            base_filename = filename_structures[shortname]
            base_filename = base_filename.replace('<date>', date)
            if '<date2>' in base_filename:
                next_day = datetime.datetime.strftime(datetime.datetime.strptime(date, '%Y%m%d') + datetime.timedelta(days=1), '%Y%m%d')
                base_filename = base_filename.replace('<date2>', next_day)

            filename = os.path.join(test_filesystem_path, base_filename)
            with open(filename, 'w') as f:
                f.write(f'File contents for {filename}')
            print(f'Created test file: {filename}')


if __name__ == '__main__':

    create_test_filesystem()
