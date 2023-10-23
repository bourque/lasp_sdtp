"""This module serves as a ``flask`` server for an API for a 'request service'
that records transactions, and parses, validates, and executes requests.

Authors
-------
    - Matthew Bourque

Example
-------

    To run a local server for development or testing purposes, use:
    ::
        FLASK_APP=request_api.py FLASK_ENV=development flask run --port 8002
"""

import logging
from pathlib import Path

from flask import abort
from flask import Flask
from flask import request

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.controller import db
from lasp_sdtp.database.queries import query_for_account_by_username
from lasp_sdtp.database.queries import query_for_filelist
from lasp_sdtp.database.queries import query_for_tags_and_extras
from lasp_sdtp.server.api_utils import CustomJSONEncoder
from lasp_sdtp.utils import utils

request_app = Flask(__name__)
request_app.json_encoder = CustomJSONEncoder
logger = logging.getLogger(__name__)


@request_app.route('/delete_file/<fileid>', methods=['DELETE'])
def delete_file(fileid: int) -> dict:
    """Parse the user-supplied ``fileid`` and record the ``DELETE`` request.

    If the ``fileid`` is not valid, a 404 error is returned.

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest.

    Returns
    -------
    response : dict
        The response object containing appropriate headers and content.
    """

    logger.info('Request to delete file %s', fileid)

    # Make sure the fileid is valid
    valid = utils.validate_fileid(fileid)
    if not valid:
        abort(400)

    # Make sure the subscriber has access to the file
    try:
        access = utils.validate_access(fileid)
    except IndexError:  # If an IndexError is raised, it means the file doesn't exist in Files table
        abort(404)
    if not access:
        abort(403)

    # Add a transactions database record
    transactionid = db.update_transactions_table(request, fileid=fileid)

    # Mark the corresponding GET request transaction as complete
    db.mark_transaction_complete(fileid)

    response = {'transactionid': str(transactionid)}

    return response


@request_app.route('/get_file/<fileid>', methods=['GET'])
def get_file(fileid: int) -> dict:
    """Parse the user-supplied ``fileid`` and record the ``GET`` request.

    If the ``fileid`` is not valid, a 400 error is returned.  If the file does
    not exist in the filesystem, a 404  error is returned.

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest.

    Returns
    -------
    response : dict
        The response object containing appropriate headers and content.
    """

    logger.info('Request for file %s', fileid)

    # Make sure the fileid is valid
    valid = utils.validate_fileid(fileid)
    if not valid:
        abort(400)

    # Make sure the subscriber has access to the file
    try:
        access = utils.validate_access(fileid)
    except IndexError:  # If an IndexError is raised, it means the file doesn't exist in File table
        abort(404)
    if not access:
        abort(403)

    # Add a transactions database record
    transactionid = db.update_transactions_table(request, fileid=fileid)

    response = {'transactionid': str(transactionid)}

    return response


@request_app.route('/get_filelist', methods=['GET'])
def get_filelist() -> dict:
    """Parse the request parameters and return a list of files available in the
    filesystem.

    If any supplied parameters in the request are not valid, a 400 error is
    returned.

    Returns
    -------
    response : dict
        The response object containing the appropriate content.
    """

    transactionid = db.update_transactions_table(request)

    # Parse parameters from the request
    tags = utils.parse_request_parameters(request)

    logger.info('Request for filelist with tags %s', tags)

    # Make sure the tags are valid
    valid = utils.validate_tags(tags)
    if not valid:
        abort(400)

    # Run the query based on the tags
    filelist = query_for_filelist(tags)

    # Get the tags & extras for the files
    fileids = [item['fileid'] for item in filelist]
    tags_and_extras = query_for_tags_and_extras(fileids)

    # Structure the file metadata, tags, and extras together into one dictionary to comply with the ICD
    data = utils.combine_metadata(filelist, tags_and_extras)

    # Apply filter for subscriber-provided tags
    data = utils.filter_for_subscriber_tags(data, tags, request)

    # Apply startfileid filter
    data = [item for item in data if item['fileid'] >= tags['startfileid']]

    # Limit the number of returned files to max_num_files
    max_num_files = min(tags['maxfile'], subscriber_config['max_num_files'])
    if len(data) > max_num_files:
        data = data[:max_num_files]

    # Rename ShortName and Version to comply with ICD
    for item in data:
        item['tags']['Version'] = item['tags'].pop('version')
        item['tags']['ShortName'] = item['tags'].pop('shortname')

    # Construct the response
    response = {'transactionid': str(transactionid),
                'results': data}

    return response


@request_app.route('/register_subscriber', methods=['PUT'])
def register_subscriber() -> dict:
    """Register a subscriber.

    See the corresponding docstrings in the ``sdtp_api.py`` module for further
    details.

    Currently, a simple string value for the certificate is used and is checked
    against a hard-coded list of acceptable certificates.

    Returns
    -------
    response : dict
        The response object containing the appropriate content.
    """

    logger.info('Request to register subscriber %s', subscriber_config['username'])

    # Check to see if the account is open for registration
    account = query_for_account_by_username(subscriber_config['username'])
    registration_open = account['registration_open']

    if registration_open:

        # Update the account with registration information
        db.update_registration()

        # Update the MissionAccountMapping with which mission(s) the subscriber is subscribed to
        db.update_mission_account_mapping()

        # Create a subscriber queue staging area for each stream
        for stream in subscriber_config['streams']:
            queue_path = Path(admin_config['staging_loc']) / subscriber_config['username'] / stream
            queue_path.mkdir(parents=True, exist_ok=True)

    else:
        logger.warning('Attempt to register account %s was made, but registration window is not open', subscriber_config['username'])
        abort(401)

    # Add a transactions database record
    transactionid = db.update_transactions_table(request)

    response = {'transactionid': transactionid}

    return response
