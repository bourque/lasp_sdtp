"""This module ingests a list of files (and their metadata) into the database.
The ``Files`` and ``TagsAndExtras`` tables are updated accordingly.

Authors
-------

    - Matthew Bourque

Use
---

    To ingest a list of files, import the ``Ingest`` class and instantiate it
    with the list of files, the stream name, and the version.  Use the
    ``ingest`` method to perform the ingest, e.g.:
    ::
        from lasp_sdtp.database.ingest import Ingest
        i = Ingest(filelist, 'prod', '01')
        i.ingest()

TODO: Make script be able to handle ingesting the same file twice
"""

import datetime
import logging
import os
import shutil
from pathlib import Path

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db
from lasp_sdtp.database.database_queries import query_for_accounts_by_mission
from lasp_sdtp.database.database_queries import query_for_mission_by_shortname
from lasp_sdtp.utils import utils


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

    def ingest(self):
        """Perform the ingest operation.  See module docstrings for further
        details.
        """

        for i, filename in enumerate(self.filelist):

            logger.info('Ingesting %s for stream %s version %s' % (Path(filename).name, self.stream, self.version))

            # Gather some metadata for the file
            shortname = utils.get_shortname(Path(filename).name)
            mission = query_for_mission_by_shortname(shortname)
            subscribed_accounts = query_for_accounts_by_mission(mission)

            # If there are subscribed accounts, proceed with the ingest process
            if subscribed_accounts:

                # Insert data into the Files table
                data = db.Files(
                    name=Path(filename).name,
                    checksum=utils.get_checksum(),
                    size=os.path.getsize(filename),
                    expires=datetime.datetime.utcnow().date() + datetime.timedelta(days=subscriber_config['expiration_period']),
                    stream=self.stream,
                    shortname=shortname,
                    version=self.version,
                    ingest_date=datetime.datetime(2022, 1, 1).date() + datetime.timedelta(days=i - 1),
                    available=True
                )
                db.session.add(data)
                db.session.flush()  # Necessary in order to get back the fileid
                fileid = data.fileid
                db.session.commit()

                # Insert data into the TagsAndExtras table
                for field_type in ['tags', 'extras']:
                    field_list = subscriber_config['streams'][self.stream][field_type]
                    for field_name in field_list:
                        value = utils.get_tag_value(filename, field_name)
                        data = [db.TagsAndExtras(
                            fileid=fileid,
                            field_name=field_name,
                            field_type=field_type[:-1],  # Remove the 's'
                            value=value
                        )]
                        db.insert_data(data)

                # Copy the files into subscriber queues who are subscribed to the data
                # and add appropriate entries to the FileQueue table
                for account in subscribed_accounts:

                    # Add entry to FileQueue table
                    data = [db.FileQueue(
                        username=account,
                        fileid=fileid,
                        entry_date=datetime.datetime.utcnow().date(),
                        expires=datetime.datetime.utcnow().date() + datetime.timedelta(days=subscriber_config['expiration_period'])
                    )]
                    db.insert_data(data)

                    # Copy file to subscriber queue
                    dst = Path(admin_config['data_cache_loc']) / account / self.stream / Path(filename).name
                    shutil.copyfile(filename, dst)
                    logger.info('Copied %s to subscriber queue: %s' % (filename, dst))
