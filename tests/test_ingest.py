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

from lasp_sdtp.config import admin_config
from lasp_sdtp.database.controller import db
from lasp_sdtp.database.ingest import Ingest


def test_ingest_not_subscribed_file():
    """Tests the ``ingest`` method with files that have no subscribers"""

    test_filename = 'not_subscribed.txt'
    test_filelist = [test_filename]

    Path(test_filename).touch(exist_ok=True)

    test_ingest = Ingest(test_filelist, 'prod', '01')
    test_ingest.ingest()

    # Check that the file wasn't actually ingested
    files = db.session.query(db.Files).filter(db.Files.name == test_filename).all()
    assert len(files) == 0


def test_ingest_subscribed_file():
    """Tests the ``ingest`` method with files that are subscribed to"""

    # Create some files to test with
    test_filelist = ['tsis2_L1_19840404.zip', 'tsis2_sc_L2_v01_19840404_19840405.zip']
    for test_file in test_filelist:
        Path(test_file).touch(exist_ok=True)

    # Ingest the files
    test_ingest = Ingest(test_filelist, 'prod', '01')
    test_ingest.ingest()

    # Query the Files table to see if the files are there
    files = db.session.query(db.Files.name).all()
    files = [item[0] for item in files]
    for test_file in test_filelist:
        assert test_file in files

        # Check that the file got copied to the subscriber queue staging area
        queue_loc = Path(admin_config['staging_loc']) / 'test_account' / 'prod' / test_file
        assert queue_loc.exists()

        # Remove the file that were just created
        Path(test_file).unlink()


def test_ingest_duplicate():
    """Tests that the ``ingest`` method is able to ingest a file that already
    exists in the system.  The original file should be removed (i.e. marked as
    unavailable in the Files table, and removed from the FileQueue table."""

    # Use the same test_filelist from the previous test that was just ingested
    test_filelist = ['tsis2_L1_19840404.zip', 'tsis2_sc_L2_v01_19840404_19840405.zip']
    for test_file in test_filelist:
        Path(test_file).touch(exist_ok=True)

    # Get the fileids of the files from the previous ingestion
    results = db.session.query(
                  db.Files
              ).filter(
                  db.Files.name.in_(test_filelist),
                  db.Files.stream == 'prod'
              ).all()
    fileids = [result.fileid for result in results]

    # Ingest the files (again)
    test_ingest = Ingest(test_filelist, 'prod', '01')
    test_ingest.ingest()

    # Make sure the original fileids are marked as unavailable (i.e. they were deleted)
    results = db.session.query(db.Files).filter(db.Files.fileid.in_(fileids)).all()
    for result in results:
        assert result.available is False

    # Make sure the original fileids are no longer in the FileQueue
    results = db.session.query(db.FileQueue).filter(db.FileQueue.fileid.in_(fileids)).all()
    assert len(results) == 0

    # Remove the file that were just created
    for test_file in test_filelist:
        Path(test_file).unlink()
