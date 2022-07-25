"""This module serves as a ``flask`` server for an API for a 'request service'
that handles user requests and records transactions.

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

from flask import abort
from flask import Flask
from flask import request
from flask.wrappers import Response
from sqlalchemy.exc import IntegrityError

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db
from lasp_sdtp.utils.utils import CustomJSONEncoder
from lasp_sdtp.utils.utils import parse_request_tags
from lasp_sdtp.utils.utils import validate_fileid
from lasp_sdtp.utils.utils import validate_tags

request_app = Flask(__name__)
request_app.json_encoder = CustomJSONEncoder
logger = logging.getLogger(__name__)


@request_app.route('/delete_file/<fileid>', methods=['DELETE'])
def delete_file(fileid: int) -> Response:
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


def get_app() -> Flask:
    """Return an instance of the flask app (used for testing purposes)

    Returns
    -------
    request_app : flask.app.Flask obj
        An instance of the flask application
    """

    return request_app


@request_app.route('/get_file/<fileid>', methods=['GET'])
def get_file(fileid: int) -> Response:
    """Parse the user-supplied ``fileid`` and record the ``GET`` request.

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
    # If the record can't be added, it means the file doesn't exist in file_metadata
    try:
        transactionid = db.update_transactions_table(request, fileid=fileid)
    except IntegrityError:
        db.session.close()  # Needed to avoid rollback during flush
        abort(404)

    response = {'transactionid': str(transactionid)}

    return response


@request_app.route('/get_filelist', methods=['GET'])
def get_filelist() -> Response:
    """Return a list of files available in the filesystem.

    If any supplied tags in the request are not valid or doesn't exist, a 400
    error is returned.

    Returns
    -------
    response : dict
        The response object containing the appropriate content.
    """

    transactionid = db.update_transactions_table(request)

    # Parse parameters from the request
    tags = parse_request_tags(request)

    # Make sure the tags are valid
    valid = validate_tags(tags)
    if not valid:
        abort(400)

    # Run the query based on the tags
    results = db.query_for_filelist(tags)

    response = {'transactionid': str(transactionid),
                'results': results}

    return response


@request_app.route('/register_subscriber', methods=['PUT'])
def register_subscriber() -> Response:
    """Register a subscriber.

    When a new subscriber is registered, an account is added to the ``accounts``
    database table and a new queue space is created in the data cache.
    Subscribers are only registered if their authentication certificate is
    valid.

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
    account = db.query_for_account(subscriber_config['username'])
    registration_open = account['registration_open']

    if registration_open:

        # Update the entry with registration information
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
        logger.warning('Attempt to register account %s was made, but registration window is not open' % subscriber_config['username'] )

    # Add a transactions database record
    transactionid = db.update_transactions_table(request)

    response = {'transactionid': transactionid}

    return response
