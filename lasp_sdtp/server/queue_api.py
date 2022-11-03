"""This module serves as a ``flask`` server for an API for a 'queue service'
that handles the operations and bookkeeping for copying/deleting files to/from
the file queue.

Authors
-------
    - Matthew Bourque

Use
---

    The ``flask`` server is intended to be run from the
    ``run_queue_service.py`` script.  Once the server is running, the
    ``flask`` app will respond to requests to the ``endpoint`` and
    ``queue_api_port`` defined  in the ``admin_config.json`` file.

    The functions within this module are intended to be called from the
    ``sdtp_api`` server, e.g.:
    ::
        requests.put('<endpoint>/delete_file/<fileid>')

    To run a local server for development or testing purposes, use:
    ::
        FLASK_APP=queue_api.py FLASK_ENV=development flask run --port 8001
"""

import datetime
import logging
import shutil
from pathlib import Path

from flask import abort
from flask import Flask
from sqlalchemy.exc import IntegrityError

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db
from lasp_sdtp.database.database_queries import query_for_files
from lasp_sdtp.database.database_queries import query_for_queue_entries


queue_app = Flask(__name__)
logger = logging.getLogger(__name__)


@queue_app.route('/delete_file/<fileid>', methods=['DELETE'])
def delete_file(fileid: int) -> dict:
    """Delete a given file from the queue, if applicable.

    See the corresponding docstrings in the ``sdtp_api.py`` module for further
    details.

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest.

    Returns
    -------
    response : dict
        The response object containing appropriate headers and content.
    """

    logger.info(f'Deleting file {fileid}')

    # Get the metadata for the file of interest
    try:
        metadata = query_for_files(fileid)
    except IndexError:  # No results, send a 404
        abort(404)

    # Determine where the file exists in the queue
    filepath = Path(admin_config['data_cache_loc']) / subscriber_config['username'] / metadata.stream / metadata.name

    # Check to see if the file is in the queue for another subscriber
    queue_entries = query_for_queue_entries(fileid)
    file_needed = False
    for entry in queue_entries:
        if entry['username'] != subscriber_config['username']:
            file_needed = True
            logger.info('File %s is needed for another subscriber and will not be deleted' % fileid)

    # If not, delete the file from the queue if it is still there
    if not file_needed:
        if filepath.exists:
            filepath.unlink(missing_ok=True)
            logger.info('Removed %s from queue' % filepath)

        # Remove entry from database
        db.delete_file_from_queue(fileid)
        logger.info('Removed fileid %s from queue' % fileid)

    return {}  # No content needed for response, but Flask expects a response that is not None


@queue_app.route('/get_file/<fileid>', methods=['GET'])
def get_file(fileid: int) -> dict:
    """Copy a file into the data cache (if it isn't already there) and return
    its contents.

    See the corresponding docstrings in the ``sdtp_api.py`` module for further
    details.

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest.

    Returns
    -------
    response : dict
        The response object containing appropriate headers and content.
    """

    logger.info('Retrieving file contents for file %s' % fileid)

    # Determine where the file exists in the filesystem
    metadata = query_for_available_files(fileid)
    filepath = Path(admin_config['filesystem_loc']) / metadata.stream / metadata.name

    # Create the parent directory where the file will be stored, if necessary
    parent_directory = Path(admin_config['data_cache_loc']) / subscriber_config['username'] / metadata.stream
    parent_directory.mkdir(parents=False, exist_ok=True)

    # Copy the file to the queue if it doesn't already exist
    dst = parent_directory / metadata.name

    try:
        shutil.copyfile(filepath, dst)
        logger.info('Copied %s to queue: %s' % (filepath, dst))

        # Add a file queue database record
        entry_date = datetime.datetime.utcnow().date()
        expiration_date = entry_date + datetime.timedelta(days=subscriber_config['expiration_period'])
        data = [{'username': subscriber_config['username'],
                 'fileid': fileid,
                 'entry_date': entry_date,
                 'expires': expiration_date}]
        db.insert_data('file_queue', data)
        logger.info('Added fileid %s to queue' % fileid)
    except IntegrityError:
        logger.warning('%s is already in the queue' % fileid)

    # Get the file contents
    with open(dst, 'r') as f:
        contents = f.readlines()

    response = {'filename': Path(dst).name, 'contents': contents}

    return response
