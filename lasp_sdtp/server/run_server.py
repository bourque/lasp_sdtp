"""The main module for running the last_sdtp flask application.

Authors
-------
    Matthew Bourque

Use
---

    To run a local server, use:
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

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_interface import FileMetadata
from lasp_sdtp.database.database_interface import FileQueue
from lasp_sdtp.database.database_interface import insert_data
from lasp_sdtp.database.database_interface import _mark_transaction_complete
from lasp_sdtp.database.database_interface import session
from lasp_sdtp.database.database_interface import _update_transactions_table
from lasp_sdtp.utils.logging import configure_logging

app = Flask(__name__)
configure_logging()


def _build_query(params):
    """Build query to the ``FileMetadata`` table to return file data based on
    user-provided parameters

    Parameters
    ----------
    params : dict
        A dictionary of key/value pairs for the request parameters

    Returns
    -------
    query:
        A ``sqlalchemy`` query of the ``FileMetadata`` table
    """

    query = session.query(FileMetadata)  # base query
    query = query.filter(FileMetadata.stream == params['stream'])  # stream is always supplied via default value
    query = query.filter(FileMetadata.version == params['version'])  # version is always supplied via default value
    if params['shortname'] != 'all':
        query = query.filter(FileMetadata.shortname == params['shortname'])
    if params['date'] is not None:
        query = query.filter(FileMetadata.date == datetime.datetime.strptime(params['date'], '%Y-%M-%d'))
    if params['start_date'] and params['end_date'] is not None:
        query = query.filter(FileMetadata.date >= datetime.datetime.strptime(params['start_date'], '%Y-%M-%d'))
        query = query.filter(FileMetadata.date <= datetime.datetime.strptime(params['end_date'], '%Y-%M-%d'))

    return query

def _parse_request_params(request):
    """Parse the params in the request and store them in a dictionary.  If any
    unsupported parameters are encountered, a 404 error is raised

    Parameters
    ----------
    request : obj
        The request to parse

    Returns
    -------
    params : dict
        A dictionary of key/value pairs for the request parameters
    """

    # Check for unsupported parameters
    supported_parameters = ['stream', 'ShortName', 'version', 'date', 'start_date', 'end_date']
    for item in request.args.keys():
        if item not in supported_parameters:
            abort(400, 'The request is incorrect') 

    params = {}

    params['stream'] = request.args.get('stream', default='prod', type=str)
    params['shortname'] = request.args.get('ShortName', default='all', type=str)
    params['version'] = request.args.get('version', default='v01', type=str)
    params['date'] = request.args.get('date', default=None, type=str)
    params['start_date'] = request.args.get('start_date', default=None, type=str)
    params['end_date'] = request.args.get('end_date', default=None, type=str)

    return params


def _validate_request_params(params):
    """Make sure that all of the provided parameters are of valid type and
    value.  If any of them are not, a 404 error is raised.

    Parameters
    ----------
    params : dict
        A dictionary of key/value pairs for the request parameters
    """

    # Make sure the date/start_date/end_date combination is valid
    # e.g. if a date is provided, the start and end dates should be None
    date_types = (type(params['date']), type(params['start_date']), type(params['end_date']))
    valid_date_type_combos = [(type(None), type(None), type(None)), (str, type(None), type(None)), (type(None), str, str)]
    if date_types not in valid_date_type_combos:
        abort(400, 'The request is incorrect')


@app.before_request
def authorize():
    """Authorize a request before it happens"""

    # Assume user is not authorized until proven otherwise
    valid_certificate = False

    # Check for a valid certificate in the header
    if 'Cert-UID' in request.headers:
        certificate = request.headers['Cert-UID']
        authorized_certificates = ['ges_disc_cert']  # Probably better to do a db lookup here
        if certificate in authorized_certificates:
            valid_certificate = True

    if not valid_certificate:
        content = 'Unauthorized'
        status = 401
        response = make_response(content, status)
        abort(response)


@app.route('/files/<fileid>', methods=['DELETE'])
def delete_file(fileid):
    """Delete a given file from the queue, if applicable.

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest.

    Returns
    -------
    response : dict
        The response object containing approriate headers and content.
    """

    # Add a transactions database record
    transactionid = _update_transactions_table(request, fileid=fileid)

    # Get the metadata for the file of interest
    file_metadata = session.query(FileMetadata).filter(FileMetadata.fileid == fileid).all()
    file_metadata = file_metadata[0].__dict__

    # Determine where the file exists in the queue
    filepath = os.path.join(admin_config['subscriber_queues_loc'], file_metadata['name'])

    # Check to see if the file is in the queue for another subscriber
    queue_data = session.query(FileQueue).filter(FileQueue.fileid == fileid).all()
    queue_data = [item.__dict__ for item in queue_data]
    file_needed = False
    for entry in queue_data:
        if entry['username'] != subscriber_config['username']:
            file_needed = True

    # If not, delete the file from the queue
    if not file_needed:
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

    fileids = [fileid for fileid in range(int(fileid_start), int(fileid_end))]
    for fileid in fileids:
        delete_file(fileid)

    # Construct the response
    content = {'message': 'Success but no other response necessary'}
    status = 204
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'

    return response


def get_app():
    """Return an instance of the flask app (mostly for testing purposes)"""
    return app


@app.route('/files/<fileid>', methods=['GET'])
def get_file(fileid):
    """Return the contents of a given file.

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest.

    Returns
    -------
    response : dict
        The response object containing approriate headers and content.
    """

    # Add a transactions database record
    transactionid = _update_transactions_table(request, fileid=fileid)

    # Get the metadata for the file of interest
    file_metadata = session.query(FileMetadata).filter(FileMetadata.fileid == fileid).all()
    file_metadata = file_metadata[0].__dict__

    # Determine where the file exists in the filesystem
    filepath = os.path.join(admin_config['filesystem_loc'], file_metadata['name'])

    # Copy the file to the queue
    dst = os.path.join(admin_config['subscriber_queues_loc'], os.path.basename(filepath))
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

    # Update transactions table with completion info
    _mark_transaction_complete(transactionid=transactionid)

    # Get the file contents
    with open(filepath, 'r') as f:
        contents = f.readlines()

    # Construct the response
    content = {'filename': os.path.basename(filepath), 'contents': contents}
    status = 200
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@app.route('/files', methods=['GET'])
def get_filelist():
    """Return a list of files available in the filesystem.

    Returns
    -------
    response : dict
        The response object containing approriate headers and content.
    """

    transactionid = _update_transactions_table(request)

    # Parse paramters from the request
    params = _parse_request_params(request)

    # Make sure the parameters are valid
    _validate_request_params(params)

    # Build and run the query based on the parameters
    query = _build_query(params)
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
    queue_path = os.path.join(admin_config['subscriber_queues_loc'], subscriber_config['username'])
    if not os.path.exists(queue_path):
        os.mkdir(queue_path)
        logging.info(f'Created queue: {queue_path}')

    # Construct the response
    content = ''
    status = 200
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


if __name__ == '__main__':

    # Register an admin account
    data = [{
        'username': 'lasp_admin',
        'role': 'admin',
        'registration_date': datetime.datetime.today()}]
    insert_data('accounts', data)
    logging.info('Registered admin account')

    app.run(host=subscriber_config['endpoint'], port='8000')
