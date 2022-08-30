"""This module serves as a ``flask`` server for an API for a 'request service'
that records transactions, and parses, validates, and executes requests.

Authors
-------
    - Matthew Bourque

Use
---

    The ``flask`` server is intended to be run from the
    ``run_request_service.py`` script.  Once the server is running, the
    ``flask`` app will respond to requests to the ``endpoint`` and
    ``request_api_port`` defined  in the ``admin_config.json`` file.

    The functions within this module are intended to be called from the
    ``sdtp_api`` server, e.g.:
    ::
        requests.put('<endpoint>/delete_file/<fileid>')

    To run a local server for development or testing purposes, use:
    ::
        FLASK_APP=request_api.py FLASK_ENV=development flask run --port 8002

TODO: Add check to make sure username is of valid type (e.g. avoid float, bool,
      etc.)
"""

import datetime
import logging
from pathlib import Path

from flask import abort
from flask import Flask
from flask import request
from sqlalchemy.exc import IntegrityError

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db
from lasp_sdtp.database.database_queries import query_for_filelist
from lasp_sdtp.database.database_queries import query_for_account
from lasp_sdtp.utils.utils import CustomJSONEncoder
from lasp_sdtp.utils.utils import parse_request_parameters
from lasp_sdtp.utils.utils import validate_fileid
from lasp_sdtp.utils.utils import validate_tags

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

    # Make sure the fileid is valid
    valid = validate_fileid(fileid)
    if not valid:
        abort(400)

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

    # Make sure the fileid is valid
    valid = validate_fileid(fileid)
    if not valid:
        abort(400)

    # Add a transactions database record
    # If the record can't be added, it means the file doesn't exist in file_metadata
    try:
        transactionid = db.update_transactions_table(request, fileid=fileid)
    except IntegrityError:
        db.session.close()  # Needed to avoid rollback during flush
        abort(404)

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
    tags = parse_request_parameters(request)

    # Make sure the tags are valid
    valid = validate_tags(tags)
    if not valid:
        abort(400)

    # Run the query based on the tags
    results = query_for_filelist(tags)

    # Limit the number of results to the max number of files
    if len(results) > subscriber_config['max_num_files']:
        results = results[:subscriber_config['max_num_files']]

    response = {'transactionid': str(transactionid),
                'results': results}

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

    # Define metadata for the entry
    certuid = f'{subscriber_config["username"]}_cert'
    registration_date = datetime.datetime.utcnow().date()
    registration_expires = registration_date + datetime.timedelta(days=subscriber_config['account_expiration_period'])

    # Check to see if the account is open for registration
    account = query_for_account(subscriber_config['username'])
    registration_open = account['registration_open']

    if registration_open:

        # Update the account with registration information
        db.update_registration()
        db.session.query(
            db.Accounts
        ).filter(
            db.Accounts.username == subscriber_config['username']
        ).update(
            {'registration_open': False,
             'certuid': certuid,
             'registration_date': registration_date,
             'registration_expires': registration_expires})
        db.session.commit()
        logger.info('Registered account for %s' % subscriber_config['username'])

        # Create a queue space in cache
        queue_path = Path(admin_config['data_cache_loc']) / subscriber_config['username']
        if not queue_path.exists:
            queue_path.mkdir()
            logger.info('Created queue: %s' % queue_path)

    else:
        logger.warning('Attempt to register account %s was made, but registration window is not open' % subscriber_config['username'])
        abort(401)

    # Add a transactions database record
    transactionid = db.update_transactions_table(request)

    response = {'transactionid': transactionid}

    return response
