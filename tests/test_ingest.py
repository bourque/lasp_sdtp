"""Tests for then ``ingest.py`` module.

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_ingest.py
"""

from pathlib import Path

from lasp_sdtp.database.database_controller import db
from lasp_sdtp.database.ingest import Ingest


def test_ingest():
    """Tests the ``ingest`` method"""

    # Create some files to test with
    test_filelist = ['tsis2_L1_test.txt', 'tsis2_sim_cal_test.txt', 'tsis2_sc_L2_test.txt']
    for test_file in test_filelist:
        Path(test_file).touch(exist_ok=True)

    # Ingest the files
    test_ingest = Ingest(test_filelist, 'prod', 'v01')
    test_ingest.ingest()

    # Query the available_files table to see if the files are there
    available_files = db.session.query(db.AvailableFiles.name).all()
    available_files = [item[0] for item in available_files]
    print(available_files)
    for test_file in test_filelist:

        assert test_file in available_files

        # Remove the file that were just created
        Path(test_file).unlink()
