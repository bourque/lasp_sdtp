"""This module serves as a ``flask`` server for an API for a 'queue service'
that handles the operations and bookkeeping for copying files to and deleting
files from the file queue.

Authors
-------
    - Matthew Bourque

Use
---

    This functions within this module are intended to be called from the
    ``sdtp_api`` server, e.g.:
    ::
        requests.put('<endpoint>/delete_file/<fileid>')
"""

import datetime
import logging
from pathlib import Path
import shutil

from flask import abort
from flask import Flask
from flask.wrappers import Response
from sqlalchemy.exc import IntegrityError

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db
from lasp_sdtp.utils.utils import CustomJSONEncoder

queue_app = Flask(__name__)
queue_app.json_encoder = CustomJSONEncoder
logger = logging.getLogger(__name__)


@queue_app.route('/delete_file/<fileid>', methods=['DELETE'])
def delete_file(fileid: int) -> Response:
    """Delete a given file from the queue, if applicable.

    A file is only deleted from the queue if it is not being used by any other
    subscriber.

    If the file of interest doesn't exist, a 404 error is returned.

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest.
    """

    logger.info(f'Deleting file {fileid}')

    # Get the metadata for the file of interest
    try:
        filename = db.query_for_filename(fileid)
    except IndexError:  # No results, send a 404
        abort(404)

    # Determine where the file exists in the queue
    filepath = Path(admin_config['data_cache_loc']) / subscriber_config['username'] / filename

    # Check to see if the file is in the queue for another subscriber
    queue_entries = db.query_for_queue_entries(fileid)
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


@queue_app.route('/get_file/<fileid>', methods=['GET'])
def get_file(fileid: int) -> Response:
    """Copy a file into the data cache (if it isn't already there) and return
    its contents.

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
    filename = db.query_for_filename(fileid)
    filepath = Path(admin_config['filesystem_loc']) / filename

    # Copy the file to the queue if it doesn't already exist
    dst = Path(admin_config['data_cache_loc']) / subscriber_config['username'] / filename

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
