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
import os
import shutil

from flask import Flask, request
from sqlalchemy import Table

from lasp_sdtp.config import config
from lasp_sdtp.database.database_interface import base, engine, FileMetadata, FileQueue, session

app = Flask(__name__)

HOME_DIR = os.path.expanduser('~')
FILESYSTEM_PATH = f'{HOME_DIR}/Desktop/test_filesystem/'
SUBSCRIBER_QUEUE = f'{HOME_DIR}/Desktop/test_queue/'


def get_app():
    """Return an instance of the flask app (mostly for testing purposes)"""
    return app


@app.route('/files', methods=['GET'])
def get_filelist():
    """Return a list of files available in the filesystem.

    Returns
    -------
    response : dict
        The response object containing approriate headers and content.
    """

    # Parse paramters from the request
    stream = request.args.get('stream', default='prod', type=str)
    shortname = request.args.get('ShortName', default='all', type=str)

    # Determine which files to return based on parameters
    if shortname == 'all':
        data = session.query(FileMetadata).all()
    else:
        data = session.query(FileMetadata).filter(FileMetadata.shortname == shortname).all()
    data = [item.__dict__ for item in data]
    for item in data:
        del item['_sa_instance_state']

    # Construct the response
    # Currently the response doesn't quite match the SDTP
    # Eventually these may be constructed based on models provided in models.py
    response = {'files': data, 'status': 200}

    return response


@app.route('/files/<fileid>', methods=['GET'])
def get_file(fileid):
    """Return the contents of a given file.

    Returns
    -------
    response : dict
        The response object containing approriate headers and content.
    """

    # Get the metadata for the file of interest
    file_metadata = session.query(FileMetadata).filter(FileMetadata.fileid == fileid).all()
    file_metadata = file_metadata[0].__dict__

    # Determine where the file exists in the filesystem
    filepath = os.path.join(FILESYSTEM_PATH, file_metadata['name'])

    # Copy the file to the queue
    dst = os.path.join(SUBSCRIBER_QUEUE, os.path.basename(filepath))
    shutil.copyfile(filepath, dst)

    # Add a database record for the file in the queue
    entry_date = datetime.datetime.today()
    expiration_date = entry_date + datetime.timedelta(days=config['expiration_period'])
    table = Table('file_queue', base.metadata)
    data_to_insert = [{'subscriber_name': 'GES DISC',
                       'fileid': fileid,
                       'entry_date': str(entry_date.strftime('%Y-%m-%d')),
                       'expires': str(expiration_date.strftime('%Y-%m-%d'))}]
    table.insert().execute(data_to_insert)

    # Get the file contents
    with open(filepath, 'r') as f:
        contents = f.readlines()

    # Build the response
    response = {'filename': file_metadata['name'], 'contents': contents, 'status': 200}

    return response


@app.route('/register', methods=['PUT'])
def register():
    """Register a subscriber.

    Returns
    -------
    response : dict
        The response object containing approriate headers and content.
    """

    # Create a queue space on filesystem

    response = {'status': 200}
    return response


@app.route('/files/<fileid>', methods=['DELETE'])
def delete_file(fileid):
    """Delete a given file from the queue, if applicable.

    Returns
    -------
    response : dict
        The response object containing approriate headers and content.
    """

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
        if entry['subscriber_name'] != 'GES DISC':
            file_needed = True

    # If not, delete the file from the queue
    if not file_needed:
        os.remove(filepath)

        # Remove entry from database
        table = Table('file_queue', base.metadata)
        table.delete().where(FileQueue.fileid == fileid).execute()

    response = {'message': 'Success but no other response necessary', 'status': 204}

    return response

@app.route('/files/<fileid_start>-<fileid_end>', methods=['DELETE'])
def delete_files(fileid_start, fileid_end):
    """
    """

    fileids = [fileid for fileid in range(int(fileid_start), int(fileid_end))]
    for fileid in fileids:
        delete_file(fileid)

    response = {'status': 204}
    return response


@app.route('/')
def home():
    """View for the homepage"""

    # Return a HTML template that describes how to use the interface?
    pass


if __name__ == '__main__':

    app.run(host=config['endpoint'], port='8000')
