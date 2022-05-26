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
import os
import shutil

from flask import abort
from flask import Flask
from flask import make_response
from flask import request
from sqlalchemy.exc import IntegrityError

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_interface import Accounts
from lasp_sdtp.database.database_interface import FileMetadata
from lasp_sdtp.database.database_interface import FileQueue
from lasp_sdtp.database.database_interface import insert_data
from lasp_sdtp.database.database_interface import _mark_transaction_complete
from lasp_sdtp.database.database_interface import session
from lasp_sdtp.database.database_interface import _update_transactions_table
from lasp_sdtp.utils.logging import configure_logging

app = Flask(__name__)
configure_logging()


def _build_query(tags):
    """Build query to the ``file_metadata`` table to return file data based on
    user-provided tags.

    For the ``date`` tag, the user may provide a specific date to filter on
    (e.g. ``date=2022-01-01``) or the user may provide a speicific date range
    to filter on via the ``start_date`` and ``end_date`` tags (e.g.
    ``start_date=2022-01-01&end_date=2022-02-01``).  If a ``date`` is provided,
    then ``start_date`` and ``end_date`` must remain as ``None``.  Alternativly,
    if both a ``start_date`` and ``end_date`` are provided, the ``date`` tag
    must remain as ``None``.

    Parameters
    ----------
    tags : dict
        A dictionary of key/value pairs for the request tags

    Returns
    -------
    query : sqlalchemy.orm.query.Query obj
        A ``sqlalchemy`` query of the ``FileMetadata`` table
    """

    query = session.query(FileMetadata)  # base query
    query = query.filter(FileMetadata.stream == tags['stream'])  # stream is always supplied via default value
    query = query.filter(FileMetadata.version == tags['version'])  # version is always supplied via default value

    # For non-default shortname values
    if tags['shortname'] != 'all':
        query = query.filter(FileMetadata.shortname == tags['shortname'])

    # For non-default date values
    if tags['date'] is not None:
        query = query.filter(FileMetadata.date == datetime.datetime.strptime(tags['date'], '%Y-%M-%d'))

    # For non-default start_date and end_date values
    if tags['start_date'] and tags['end_date'] is not None:
        query = query.filter(FileMetadata.date >= datetime.datetime.strptime(tags['start_date'], '%Y-%M-%d'))
        query = query.filter(FileMetadata.date <= datetime.datetime.strptime(tags['end_date'], '%Y-%M-%d'))

    return query


def _parse_request_tags(request):
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
    supported_tags = ['stream', 'ShortName', 'version', 'date', 'start_date', 'end_date']
    for item in request.args.keys():
        if item not in supported_tags:
            abort(400)

    # Store supplied tags in a dictionary
    tags = {}
    tags['stream'] = request.args.get('stream', default='prod', type=str)
    tags['shortname'] = request.args.get('ShortName', default='all', type=str)
    tags['version'] = request.args.get('version', default='v01', type=str)
    tags['date'] = request.args.get('date', default=None, type=str)
    tags['start_date'] = request.args.get('start_date', default=None, type=str)
    tags['end_date'] = request.args.get('end_date', default=None, type=str)

    return tags


def _register_admin():
    """Resiters an ``admin`` account if it doesn't already exist"""

    # Check if an admin account already exists
    results = session.query(Accounts).filter(Accounts.username == 'lasp_admin').all()

    # If it doesn't, create one
    if not results:
        data = [{
            'username': 'lasp_admin',
            'certuid': 'admin_cert',
            'role': 'admin',
            'registration_date': datetime.datetime.today()}]
        insert_data('accounts', data)
        logging.info('Registered admin account')


def _validate_fileid(fileid):
    """Make sure that the provided ``fileid`` is a positive integer that is 15
    digits or less.  If it is not, a 400 error is raised.

    Parameters
    ----------
    fileid : str
        The ``fileid`` given in the request
    """

    # Make sure given fileid is an integer
    try:
        int(fileid)
    except ValueError:
        abort(400)

    # Make sure the given fileid is a positive integer that is 15 digits or less
    if int(fileid) <= 0 or int(fileid) > 999999999999999:
        abort(400)


def _validate_tags(tags):
    """Make sure that all of the provided tags are of valid type and value.  If
    any of them are not, a 404 error is raised.

    Parameters
    ----------
    tags : dict
        A dictionary of key/value pairs for the request tags
    """

    # Make sure the date/start_date/end_date combination is valid
    # e.g. if a date is provided, the start and end dates should be None
    date_types = (type(tags['date']), type(tags['start_date']), type(tags['end_date']))
    valid_date_type_combos = [(type(None), type(None), type(None)), (str, type(None), type(None)), (type(None), str, str)]
    if date_types not in valid_date_type_combos:
        abort(400)


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
def custom400(error):
    """Returns custom 400 response"""
    return make_response({'message': 'The request is incorrect'}, 400)


@app.errorhandler(401)
def custom401(error):
    """Returns custom 401 response"""

    # The message depends on the request method
    if request.method == 'PUT':
        return make_response({'message': 'Unauthorized'}, 401)
    elif request.method == 'GET':
        return make_response({'message': 'Request is not authenticated'}, 401)


@app.errorhandler(404)
def custom404(error):
    """Returns custom 400 response"""
    return make_response({'message': 'The requested resource does not exist'}, 404)


@app.route('/files/<fileid>', methods=['DELETE'])
def delete_file(fileid):
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
    _validate_fileid(fileid)

    # Add a transactions database record
    transactionid = _update_transactions_table(request, fileid=fileid)

    # Mark the corresponding GET request transaction as complete
    _mark_transaction_complete(fileid)

    # Get the metadata for the file of interest
    try:
        file_metadata = session.query(FileMetadata.name).filter(FileMetadata.fileid == fileid).all()
        filename = file_metadata[0][0]
    except IndexError:  # No results, send a 404
        abort(404)

    # Determine where the file exists in the queue
    filepath = os.path.join(admin_config['data_cache_loc'], subscriber_config['username'], filename)

    # Check to see if the file is in the queue for another subscriber
    queue_data = session.query(FileQueue).filter(FileQueue.fileid == fileid).all()
    queue_data = [item.__dict__ for item in queue_data]
    file_needed = False
    for entry in queue_data:
        if entry['username'] != subscriber_config['username']:
            file_needed = True

    # If not, delete the file from the queue if it is still there
    if not file_needed:
        if os.path.exists(filepath):
            os.remove(filepath)
            logging.info(f'Removed {filepath} from queue')

        # Remove entry from database
        session.query(FileQueue).filter(FileQueue.fileid == fileid).delete()
        session.commit()
        logging.info(f'Removed fileid {fileid} from queue')

    # Construct the response
    content = {'message': 'Success but no other response necessary'}
    status = 204
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@app.route('/files/<fileid_start>-<fileid_end>', methods=['DELETE'])
def delete_files(fileid_start, fileid_end):
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


def get_app():
    """Return an instance of the flask app (used for testing purposes)

    Returns
    -------
    app : flask.app.Flask obj
        An instance of the flask application
    """

    return app


@app.route('/files/<fileid>', methods=['GET'])
def get_file(fileid):
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
    _validate_fileid(fileid)

    # Add a transactions database record
    # If the record cant be added, it means the file doesn't exist in file_metadata
    try:
        transactionid = _update_transactions_table(request, fileid=fileid)
    except IntegrityError:
        session.close()  # Needed to avoid rollback during flush
        abort(404)


    # Get the filename for the file of interest
    file_metadata = session.query(FileMetadata.name).filter(FileMetadata.fileid == fileid).all()
    filename = file_metadata[0][0]

    # Determine where the file exists in the filesystem
    filepath = os.path.join(admin_config['filesystem_loc'], filename)

    # Copy the file to the queue if it doesn't already exist
    dst = os.path.join(admin_config['data_cache_loc'], subscriber_config['username'], filename)

    try:
        shutil.copyfile(filepath, dst)
        logging.info(f'Copied {filepath} to queue: {dst}')

        # Add a file queue database record
        entry_date = datetime.datetime.today()
        expiration_date = entry_date + datetime.timedelta(days=subscriber_config['expiration_period'])
        data = [{'username': subscriber_config['username'],
                 'fileid': fileid,
                 'entry_date': entry_date,
                 'expires': expiration_date}]
        insert_data('file_queue', data)
        logging.info(f'Added fileid {fileid} to queue')
    except IntegrityError:
        logging.warning(f'{fileid} is already in the queue')

    # Get the file contents
    with open(dst, 'r') as f:
        contents = f.readlines()

    # Construct the response
    content = {'filename': os.path.basename(dst), 'contents': contents}
    status = 200
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@app.route('/files', methods=['GET'])
def get_filelist():
    """Return a list of files available in the filesystem.

    If any supplied tags in the request are not valid or doesn't exist, a 400
    error is returned.

    Returns
    -------
    response : dict
        The response object containing approriate headers and content.
    """

    transactionid = _update_transactions_table(request)

    # Parse paramters from the request
    tags = _parse_request_tags(request)

    # Make sure the tags are valid
    _validate_tags(tags)

    # Build and run the query based on the tags
    query = _build_query(tags)
    results = query.all()

    # Parse the query results
    data = [item.__dict__ for item in results]
    for item in data:
        del item['_sa_instance_state']

    # Construct the response
    content = {'files': data}
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
def register():
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
    registration_date = datetime.datetime.today()
    registration_expires = registration_date + datetime.timedelta(days=subscriber_config['account_expiration_period'])
    data = [{
        'username': subscriber_config['username'],
        'role': 'subscriber',
        'certuid': f'{subscriber_config["username"]}_cert',
        'registration_date': registration_date,
        'registration_expires': registration_expires}]
    insert_data('accounts', data)
    logging.info(f'Registered account for {subscriber_config["username"]}')

    # Add a transactions database record
    transactionid = _update_transactions_table(request)

    # Create a queue space in cache
    queue_path = os.path.join(admin_config['data_cache_loc'], subscriber_config['username'])
    if not os.path.exists(queue_path):
        os.mkdir(queue_path)
        logging.info(f'Created queue: {queue_path}')

    # Construct the response
    content = {'message': 'Success but no other response necessary'}
    status = 204
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


if __name__ == '__main__':

    # Register an admin account if necessary
    _register_admin()

    # Run the server
    app.run(host=admin_config['endpoint'], port='8000')
