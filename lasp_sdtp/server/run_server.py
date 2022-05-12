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
from sqlalchemy import Table

from lasp_sdtp.config import config
from lasp_sdtp.database.database_interface import base
from lasp_sdtp.database.database_interface import FileMetadata
from lasp_sdtp.database.database_interface import FileQueue
from lasp_sdtp.database.database_interface import _mark_transaction_complete
from lasp_sdtp.database.database_interface import session
from lasp_sdtp.database.database_interface import _update_transactions_table
from lasp_sdtp.utils.utils import configure_logging

app = Flask(__name__)
configure_logging()

HOME_DIR = os.path.expanduser('~')
FILESYSTEM_PATH = f'{HOME_DIR}/Desktop/test_filesystem/'
SUBSCRIBER_QUEUE = f'{HOME_DIR}/Desktop/test_queue/'


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
    filepath = os.path.join(SUBSCRIBER_QUEUE, file_metadata['name'])

    # Check to see if the file is in the queue for another subscriber
    queue_data = session.query(FileQueue).filter(FileQueue.fileid == fileid).all()
    queue_data = [item.__dict__ for item in queue_data]
    file_needed = False
    for entry in queue_data:
        if entry['username'] != config['username']:
            file_needed = True

    # If not, delete the file from the queue
    if not file_needed:
        os.remove(filepath)
        logging.info(f'Removed {filepath} from queue')

        # Remove entry from database
        table = Table('file_queue', base.metadata)
        table.delete().where(FileQueue.fileid == fileid).execute()
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
    filepath = os.path.join(FILESYSTEM_PATH, file_metadata['name'])

    # Copy the file to the queue
    dst = os.path.join(SUBSCRIBER_QUEUE, os.path.basename(filepath))
    shutil.copyfile(filepath, dst)
    logging.info(f'Copied {filepath} to queue: {dst}')

    # Add a file queue database record
    entry_date = datetime.datetime.today()
    expiration_date = entry_date + datetime.timedelta(days=config['expiration_period'])
    table = Table('file_queue', base.metadata)
    data_to_insert = [{'username': config['username'],
                       'fileid': fileid,
                       'entry_date': entry_date,
                       'expires': expiration_date}]
    table.insert().execute(data_to_insert)
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
    stream = request.args.get('stream', default='prod', type=str)
    shortname = request.args.get('ShortName', default='all', type=str)
    version = request.args.get('version', default='v01', type=str)

    # Determine which files to return based on parameters
    query = session.query(FileMetadata)\
        .filter(FileMetadata.stream == stream)\
        .filter(FileMetadata.version == version)
    if shortname != 'all':
        query = query.filter(FileMetadata.shortname == shortname)
    results = query.all()

    # Parse the results
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
    registration_expires = registration_date + datetime.timedelta(days=config['account_expiration_period'])
    table = Table('accounts', base.metadata)
    data_to_insert = [{
        'username': config['username'],
        'role': 'subscriber',
        'certuid': f'{config["username"]}_cert',
        'registration_date': registration_date,
        'registration_expires': registration_expires}]
    table.insert().execute(data_to_insert)
    logging.info(f'Registered account for {config["username"]}')

    # Add a transactions database record
    transactionid = _update_transactions_table(request)

    # Create a queue space on filesystem
    queue_path = f"{HOME_DIR}/Desktop/{config['username']}_queue/"
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
    data_to_insert = [{
        'username': 'lasp_admin',
        'role': 'admin',
        'registration_date': datetime.datetime.today()}]
    Table('accounts', base.metadata).insert().execute(data_to_insert)
    logging.info('Registered admin account')

    app.run(host=config['endpoint'], port='8000')
