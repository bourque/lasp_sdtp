"""This module serves as a ``flask`` server for an API for a 'queue service'
that handles the operations and bookkeeping for copying/deleting files to/from
the file queue.

Authors
-------
    - Matthew Bourque

Use
---

    The ``flask`` server can be started from the ``run_queue_service.py``
    script.  Once the server is running, the ``flask`` app will respond to
    requests to the ``endpoint`` and ``queue_api_port`` defined  in the
    ``admin_config.json`` file.

    The functions within this module are intended to be called from the
    ``sdtp_api`` server, e.g.:
    ::
        requests.put('<endpoint>/delete_file/<fileid>')

    To run a local server for development or testing purposes, use:
    ::
        FLASK_APP=queue_api.py FLASK_ENV=development flask run --port 8001
"""

import logging
from pathlib import Path

from flask import abort
from flask import Flask

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db
from lasp_sdtp.database.database_queries import query_for_file
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

    logger.info('Deleting file %s', fileid)

    # Get the metadata for the file of interest
    try:
        metadata = query_for_file(fileid)
    except IndexError:  # No results, send a 404
        abort(404)

    # Determine where the file exists in the subscriber queue staging area
    file_loc = Path(admin_config['staging_loc']) / subscriber_config['username'] / metadata.stream / metadata.name

    # Check to see if the file is in the queue for another subscriber
    queue_entries = query_for_queue_entries(fileid)
    file_needed = False
    for entry in queue_entries:
        if entry['username'] != subscriber_config['username']:
            file_needed = True
            logger.debug('File %s is needed for another subscriber and will not be deleted', fileid)

    # If not, delete the file from the subscriber queue staging area if it is still there
    if not file_needed:
        if file_loc.exists:
            file_loc.unlink(missing_ok=True)
            logger.debug('Removed %s from queue', file_loc)
        else:
            logger.warning('Could not access %s, though it is expected to exist', file_loc)

        # Remove entry from the FileQueue table
        db.delete_file_from_queue(fileid)
        logger.debug('Removed fileid %s from queue', fileid)

        # Update Files table to indicate that the file is no longer available
        db.mark_as_deleted(fileid)

    return {}  # No content needed for response, but Flask expects a response that is not None


@queue_app.route('/get_file/<fileid>', methods=['GET'])
def get_file(fileid: int) -> dict:
    """Return the contents of the requested file

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

    logger.info('Retrieving file contents for file %s', fileid)

    # Determine where the file exists in the subscriber queue staging area
    metadata = query_for_file(fileid)
    file_loc = Path(admin_config['staging_loc']) / subscriber_config['username'] / metadata.stream / metadata.name

    # If the file doesn't exist, raise a 404 error
    if not file_loc.exists():
        abort(404)

    # Get the file contents
    with open(file_loc, 'r') as f:
        contents = f.readlines()

    response = {'filename': Path(file_loc).name, 'contents': contents}

    return response
