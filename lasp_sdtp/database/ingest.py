"""This module ingests a list of files (and their metadata) into the database.
The ``Files`` and ``TagsAndExtras`` tables are updated accordingly.

If a file already exists in the system (i.e. it is in one or more subscriber
queues and is marked as available in the ``Files`` table), the file is 'purged'
from the system (i.e. it is removed from subscriber queue staging area and
marked as unavailable/deleted in the ``Files`` table)

Authors
-------

    - Matthew Bourque

Example
-------

    To ingest a list of files, import the ``Ingest`` class and instantiate it
    with the list of files, the stream name, and the version.  Use the
    ``ingest`` method to perform the ingest, e.g.:
    ::
        from lasp_sdtp.database.ingest import Ingest
        i = Ingest(filelist, 'prod', '01')
        i.ingest()
"""

import datetime
import logging
import os
import shutil
from pathlib import Path

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.controller import db
from lasp_sdtp.database.queries import query_for_accounts_by_mission
from lasp_sdtp.database.queries import query_for_mission_by_shortname
from lasp_sdtp.utils import utils
from lasp_sdtp.utils.properties import TEST_FILES_TO_IGNORE


logger = logging.getLogger(__name__)


class Ingest():
    """A class for ingesting a list of files into the database.

    Attributes
    ----------
    filelist : list
        A list of paths to files to ingest.
    stream : str
        The stream associated with the files and ingestion (e.g. ``prod``).
    version : str
        The version associated with the files and ingestion (e.g. ``01``).

    Methods
    -------
    ingest()
        Ingest the files into the database
    """

    def __init__(self, filelist: list, stream: str, version: str):

        self.filelist = filelist
        self.stream = stream
        self.version = version

    def _copy_to_subscriber_queue(self, file: str, account: str):
        """Copy the given file to the appropriate subscriber queue staging area

        Parameters
        ----------
        file : str
            The path to the file to copy
        account : str
            The account associated with the subscriber queue space to copy the
            file to (e.g. ``ges_disc``)
        """

        # Copy file to subscriber queue
        dst = Path(admin_config['staging_loc']) / account / self.stream / Path(file).name
        shutil.copyfile(file, dst)
        logger.info('Copied file %s to subscriber queue: %s',  (file, dst))

    def _get_filelist_to_ingest(self) -> list:
        """Determine which files need to be ingested based on which files are
        already in the database.

        Returns
        -------
        filelist_to_ingest : list[str]
        """

        files_in_db = db.session.query(db.Files).filter(db.Files.stream == self.stream).all()
        files_in_db = [item.name for item in files_in_db]

        files_to_ingest = [file for file in self.filelist if Path(file).name not in files_in_db]

        return files_to_ingest

    def _insert_into_filequeue(self, fileid: int, account: str):
        """Insert the given file into the ``FileQueue`` table for the given
        ``account``.

        Parameters
        ----------
        fileid : int
            The ``fileid`` of the file to put in the queue
        account : str
            The username of the account for the subscriber queue of interest
            (e.g. ``ges_disc``)
        """

        # The file shall expire just before UTC midnight
        expires = datetime.datetime.combine(
            datetime.datetime.utcnow().date() + datetime.timedelta(days=subscriber_config['expiration_period']),
            datetime.time(11, 59, 59)
        )

        data = [db.FileQueue(
            username=account,
            fileid=fileid,
            entry_date=datetime.datetime.utcnow().date(),
            expires=expires
        )]
        db.insert_data(data)
        logger.debug('Inserted file %s into FileQueue for account %s', (fileid, account))

    def _insert_into_files(self, file: str, shortname: str) -> int:
        """Insert data associated with the given file into the ``Files`` table.

        Parameters
        ----------
        file : str
            The path to the file of interest
        shortname
            The ``shortname`` for the file (e.g. ``TSIS2_L1``)

        Returns
        -------
        fileid : int
            The ``fileid`` that was used when inserting an entry into the
            ``Files`` table.
        """

        # The file shall expire just before UTC midnight
        expires = datetime.datetime.combine(
            datetime.datetime.utcnow().date() + datetime.timedelta(days=subscriber_config['expiration_period']),
            datetime.time(11, 59, 59)
        )

        data = db.Files(
            name=Path(file).name,
            checksum=utils.get_checksum(file),
            size=os.path.getsize(file),
            expires=expires,
            stream=self.stream,
            shortname=shortname,
            version=self.version,
            ingest_date=datetime.datetime.utcnow().date(),
            available=True
        )
        db.session.add(data)
        db.session.flush()  # Necessary in order to get back the fileid
        fileid = data.fileid
        db.session.commit()

        logger.debug('Inserted file %s into Files table', file)

        return fileid

    def _insert_into_tagsandextras(self, file: str, fileid: str):
        """Insert subscriber tags and extras associated with the given ``file``
        into the ``TagsAndExtras`` table

        Parameters
        ----------
        file : str
            The path to the file of interest
        fileid
            The ``fileid`` of the given ``file``
        """

        for field_type in ['tags', 'extras']:
            field_list = subscriber_config['streams'][self.stream][field_type]
            for field_name in field_list:
                value = utils.get_tag_value(file, field_name)
                data = [db.TagsAndExtras(
                    fileid=fileid,
                    field_name=field_name,
                    field_type=field_type[:-1],  # Remove the 's'
                    value=value
                )]
                db.insert_data(data)

        logger.debug('Inserted tags and extras metadata for file %s into TagsAndExtras table', file)

    def _purge_file(self, fileid, filename: str, accounts: list):
        """Purges the given file from the system for the provided accounts.
        The file is removed from the accounts queue space, removed from the
        ``FileQueue`` table, and marked as unavailable in the ``Files`` table.

        Parameters
        ----------
        filename : str
            The name of the file to purge (e.g. ``tsis2_sim_cal_v01.zip``)
        accounts : list of str
            A list of account usernames to purge the file from
        """

        # Remove file from subscriber queue staging area
        for account in accounts:
            filepath = Path(admin_config['staging_loc']) / account / self.stream / filename
            filepath.unlink()
            logger.debug('Removed file %s from subscriber queue staging area for account %s', (filepath, account))

        # Remove the file from FileQueue table
        db.session.query(db.FileQueue).filter(db.FileQueue.fileid == fileid).delete()

        # Mark the file as deleted in the Files table
        db.mark_as_deleted(fileid)

        logger.info('Purged file %s', fileid)

    def ingest(self):
        """Perform the ingest operation.  See module docstrings for further
        details.
        """

        logging.info('Ingesting files for stream %s version %s', self.stream, self.version)

        # Only ingest files that are not already in the database
        filelist_to_ingest = self._get_filelist_to_ingest()

        logging.info('Files to ingest: %s', filelist_to_ingest)

        for file in filelist_to_ingest:

            filename = Path(file).name

            logger.info('Ingesting file: %s', filename)

            # Validate the shortname
            try:
                shortname = utils.get_shortname(filename)
            except TypeError:
                logger.warning('No matching shortname found for %s', filename)
                Path(file).unlink()
                logger.debug('Deleted file %s', file)
                continue

            # Make sure file is not empty
            if filename not in TEST_FILES_TO_IGNORE:
                filesize = os.path.getsize(file)
                if not filesize:
                    logger.warning('Unexpected empty file for %s', filename)
                    Path(file).unlink()
                    logger.debug('Deleted file %s', filename)
                    continue

            # Gather some more information from the file
            mission = query_for_mission_by_shortname(shortname)
            subscribed_accounts = query_for_accounts_by_mission(mission)

            # If there are subscribed accounts, proceed with the ingest process
            if subscribed_accounts:

                # Check to see if the file already exists (and is available in the system)
                # If it is, then purge the existing file so that it can be replaced with the new one
                existing_file = db.session.query(
                    db.Files
                ).filter(
                    db.Files.name == filename,
                    db.Files.available == True,
                    db.Files.stream == self.stream
                ).one_or_none()
                if existing_file:
                    fileid_to_purge = existing_file.fileid
                    self._purge_file(fileid_to_purge, filename, subscribed_accounts)

                # Insert data into the Files table
                fileid = self._insert_into_files(file, shortname)

                # Insert data into the TagsAndExtras table
                self._insert_into_tagsandextras(file, fileid)

                # Copy the file into subscriber queues who are subscribed to the data
                # and add appropriate entries to the FileQueue table
                for account in subscribed_accounts:
                    self._insert_into_filequeue(fileid, account)
                    self._copy_to_subscriber_queue(file, account)

            else:
                logger.warning('No subscribed accounts for %s', file)
                Path(file).unlink()
                logger.debug('Deleted file %s', file)

        logging.info('Ingestion complete')
