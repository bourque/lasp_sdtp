"""The main module for running the ``last_sdtp`` flask application.

Authors
-------
    Matthew Bourque

Use
---

    If this module is executed via the command line, an ``admin`` account is
    registered and the server is run from the ``endpoint`` defined in the
    ``admin_config.json`` file.  A log file is also created, the path to which
    will be printed to the terminal.

    To run a local server for development or testing purposes, use:
    ::
        FLASK_APP=server.py FLASK_ENV=development flask run --port 8000
"""

import datetime
import logging
import shutil
from pathlib import Path

from flask import abort
from flask import Flask
from flask import make_response
from flask import request
from flask.wrappers import Response
from sqlalchemy.exc import IntegrityError
from werkzeug import exceptions

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db

logger = logging.getLogger(__name__)
app = Flask(__name__)


def _parse_request_tags(request: object) -> dict:
    """Parse the tags in the request and store them in a dictionary.  If any
    unsupported tags are encountered, a 404 error is raised.

    Parameters
    ----------
    request : obj
        The request to parse

    Returns
    -------
    tags : dict
        A dictionary of key/value pairs for the request tags
    """

    # Check for unsupported tags
    supported_tags = [
        ('stream', 'prod', str),
        ('ShortName', 'all', str),
        ('version', 'v01', str),
        ('date', None, str),
        ('start_date', None, str),
        ('end_date', None, str)]
    for item in request.args.keys():
        if item not in [item[0] for item in supported_tags]:
            abort(400)

    # Store supplied tags in a dictionary
    tags = {}
    for item in supported_tags:
        tags[item[0].lower()] = request.args.get(item[0], default=item[1], type=item[2])

    return tags


def _validate_fileid(fileid: str) -> bool:
    """Make sure that the provided ``fileid`` is a positive integer that is 15
    digits or less.  If it is not, a 400 error is raised.

    Parameters
    ----------
    fileid : str
        The ``fileid`` given in the request
    Returns
    -------
    bool
        True or False for whether or not the ``fileid`` is valid
    """

    # Make sure given fileid is an integer
    try:
        int(fileid)
    except ValueError:
        return False

    # Make sure the given fileid is a positive integer that is 15 digits or less
    if int(fileid) <= 0 or int(fileid) > 999999999999999:
        return False
    else:
        return True


def _validate_tags(tags: dict) -> bool:
    """Make sure that all of the provided tags are of valid type and value.  If
    any of them are not, a 404 error is raised.

    Parameters
    ----------
    tags : dict
        A dictionary of key/value pairs for the request tags

    Returns
    -------
    bool
        True or False for whether or not the tags are valid
    """

    # Make sure the date/start_date/end_date combination is valid
    # e.g. if a date is provided, the start and end dates should be None
    date_types = (type(tags['date']), type(tags['start_date']), type(tags['end_date']))
    valid_date_type_combos = [(type(None), type(None), type(None)), (str, type(None), type(None)), (type(None), str, str)]
    if date_types not in valid_date_type_combos:
        return False
    else:
        return True


@app.before_request
def authorize():
    """Authorize a request.  This is performed before every request is processed"""

    # Assume user is not authorized until proven otherwise
    valid_certificate = False

    # Check for a valid certificate in the header
    if 'Cert-UID' in request.headers:
        certificate = request.headers['Cert-UID']
        authorized_certificates = ['ges_disc_cert']  # Probably better to do a db lookup here?
        if certificate in authorized_certificates:
            valid_certificate = True

    if not valid_certificate:
        abort(401)


@app.errorhandler(400)
def custom400(error: exceptions.BadRequest) -> Response:
    """Returns custom 400 response"""
    return make_response({'message': 'The request is incorrect'}, 400)


@app.errorhandler(401)
def custom401(error: exceptions.Unauthorized) -> Response:
    """Returns custom 401 response"""

    # The message depends on the request method
    if request.method == 'PUT':
        return make_response({'message': 'Unauthorized'}, 401)
    elif request.method == 'GET':
        return make_response({'message': 'Request is not authenticated'}, 401)


@app.errorhandler(404)
def custom404(error: exceptions.NotFound) -> Response:
    """Returns custom 400 response"""
    return make_response({'message': 'The requested resource does not exist'}, 404)


@app.route('/files/<fileid>', methods=['DELETE'])
def delete_file(fileid: int) -> Response:
    """Delete a given file from the queue, if applicable.

    A file is only deleted from the queue if it is not being used by any other
    subscriber.

    If the file of interest doesn't exist, a 404 error is returned.

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest.

    Returns
    -------
    response : dict
        The response object containing approriate headers and content.
    """

    # Make sure the fileid is valid
    valid = _validate_fileid(fileid)
    if not valid:
        abort(400)

    # Add a transactions database record
    transactionid = db.update_transactions_table(request, fileid=fileid)

    # Mark the corresponding GET request transaction as complete
    db.mark_transaction_complete(fileid)

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

    # If not, delete the file from the queue if it is still there
    if not file_needed:
        if filepath.exists:
            filepath.unlink(missing_ok=True)
            logger.info('Removed %s from queue' % filepath)

        # Remove entry from database
        db.delete_file_from_queue(fileid)
        logger.info('Removed fileid %s from queue' % fileid)

    # Construct the response
    content = {'message': 'Success but no other response necessary'}
    status = 204
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@app.route('/files/<fileid_start>-<fileid_end>', methods=['DELETE'])
def delete_files(fileid_start: int, fileid_end: int) -> Response:
    """For a range of files, delete those that are no longer needed in the queue

    Parameters
    ----------
    fileid_start : int
        The starting ``fileid`` of interest.
    fileid_end : int
        The ending ``fileid`` of interest.

    Returns
    -------
    response : dict
        The response object containing approriate headers and content.
    """

    # Iterate through the files and delete them individually
    fileids = [fileid for fileid in range(int(fileid_start), int(fileid_end) + 1)]
    for fileid in fileids:
        delete_file(fileid)

    # Construct the response
    content = {'message': 'Success but no other response necessary'}
    status = 204
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'

    return response


def get_app() -> Flask:
    """Return an instance of the flask app (used for testing purposes)

    Returns
    -------
    app : flask.app.Flask obj
        An instance of the flask application
    """

    return app


@app.route('/files/<fileid>', methods=['GET'])
def get_file(fileid: int) -> Response:
    """Return the contents of a given file.

    If the supplied ``fileid`` is not a valid positive integer, a 404 error is
    returned.  Also, if the file does not exist, a 404 error is returned.

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest.

    Returns
    -------
    response : dict
        The response object containing approriate headers and content.
    """

    # Make sure the fileid is valid
    valid = _validate_fileid(fileid)
    if not valid:
        abort(400)

    # Add a transactions database record
    # If the record cant be added, it means the file doesn't exist in file_metadata
    try:
        transactionid = db.update_transactions_table(request, fileid=fileid)
    except IntegrityError:
        db.session.close()  # Needed to avoid rollback during flush
        abort(404)

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

    # Construct the response
    content = {'filename': Path(dst).name, 'contents': contents}
    status = 200
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@app.route('/files', methods=['GET'])
def get_filelist() -> Response:
    """Return a list of files available in the filesystem.

    If any supplied tags in the request are not valid or doesn't exist, a 400
    error is returned.

    Returns
    -------
    response : dict
        The response object containing approriate headers and content.
    """

    transactionid = db.update_transactions_table(request)

    # Parse paramters from the request
    tags = _parse_request_tags(request)

    # Make sure the tags are valid
    valid = _validate_tags(tags)
    if not valid:
        abort(400)

    # Run the query based on the tags
    results = db.query_for_filelist(tags)

    # Construct the response
    content = {'files': results}
    status = 200
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@app.route('/')
def home():
    """View for the homepage"""

    # Return a HTML template that describes how to use the interface?
    pass


@app.route('/register', methods=['PUT'])
def register() -> Response:
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
        The response object containing approriate headers and content.
    """

    # Add a accounts database record
    registration_date = datetime.datetime.utcnow().date()
    registration_expires = registration_date + datetime.timedelta(days=subscriber_config['account_expiration_period'])
    data = [{
        'username': subscriber_config['username'],
        'role': 'subscriber',
        'certuid': f'{subscriber_config["username"]}_cert',
        'registration_date': registration_date,
        'registration_expires': registration_expires}]
    db.insert_data('accounts', data)
    logger.info('Registered account for %s' % subscriber_config['username'])

    # Add a transactions database record
    transactionid = db.update_transactions_table(request)

    # Create a queue space in cache
    queue_path = Path(admin_config['data_cache_loc']) / subscriber_config['username']
    if not queue_path.exists:
        queue_path.mkdir()
        logger.info('Created queue: %s' % queue_path)

    # Construct the response
    content = {'message': 'Success but no other response necessary'}
    status = 204
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


def register_admin():
    """Resiters an ``admin`` account if it doesn't already exist"""

    # Check if an admin account already exists
    account = db.query_for_account('lasp_admin')

    # If it doesn't, create one
    if not account:
        data = [{
            'username': 'lasp_admin',
            'certuid': 'admin_cert',
            'role': 'admin',
            'registration_date': datetime.datetime.utcnow().date()}]
        db.insert_data('accounts', data)
        logger.info('Registered admin account')
