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
        i = Ingest(filelist, 'prod', 'v01')
        i.ingest()

TODO: Get the actual Tags/Extra values to store in the database
"""

import datetime
import logging
import os
from pathlib import Path

from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db
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
        The version associated with the files and ingestion (e.g. ``v01``).
    data_product_id : str
        The data product ID associated with the files (e.g. ``tsis2``).

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

            # Gather data for available_files table
            data = db.Files(
                name=Path(filename).name,
                checksum=utils.get_checksum(),
                size=os.path.getsize(filename),
                expires=datetime.datetime.utcnow().date() + datetime.timedelta(days=subscriber_config['expiration_period']),
                stream=self.stream,
                shortname=utils.get_shortname(Path(filename).name),
                version=self.version,
                ingestDate=datetime.datetime(2022, 1, 1).date() + datetime.timedelta(days=i - 1),
                available=True
            )

            # Insert the data, get back the fileid
            db.session.add(data)
            db.session.flush()
            fileid = data.fileid
            db.session.commit()

            # Gather data for metadata table
            for field_type in ['tags', 'extras']:
                field_list = subscriber_config['streams'][self.stream][field_type]
                for field_name in field_list:
                    # value = utils.get_tag_value(filename, field)
                    value = 'some_value'
                    data = {
                        'fileid': fileid,
                        'field_name': field_name,
                        'field_type': field_type[:-1],  # Remove the 's'
                        'value': value
                    }
                    db.insert_data('metadata', [data])
