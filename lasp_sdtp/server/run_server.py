"""The main module for running the last_sdtp flask application

Authors
-------
    Matthew Bourque

Use
---

    To run a local server, use:
        FLASK_APP=server.py FLASK_ENV=development flask run --port 8000
"""

import os

from flask import Flask
from flask import request

from lasp_sdtp.database.database_interface import FileMetadata, session

app = Flask(__name__)

HOME_DIR = os.path.expanduser('~')
FILESYSTEM_PATH = f'{HOME_DIR}/Desktop/test_filesystem/'


def create_app():
    """
    """

    return app

@app.route('/files', methods=['GET'])
def get_filelist():

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

    # Get the metadata for the file of interest
    data = session.query(FileMetadata).filter(FileMetadata.fileid == fileid).all()
    data = data[0].__dict__

    # Determine where the file exists in the filesystem
    filepath = os.path.join(FILESYSTEM_PATH, data['name'])

    # Get the file contents
    with open(filepath, 'r') as f:
        contents = f.readlines()

    response = {'contents': contents, 'status': 200}

    return response


@app.route('/register', methods=['PUT'])
def register():
    
    response = {'status': 200}
    return response


@app.route('/files/<fileid>', methods=['DELETE'])
def delete_file(fileid):

    # Get the metadata for the file of interest
    data = session.query(FileMetadata).filter(FileMetadata.fileid == fileid).all()
    data = data[0].__dict__

    # Determine where the file exists in the filesystem
    filepath = os.path.join(FILESYSTEM_PATH, data['shortname'], data['name'])

    # # Check to see if the file is in the queue
    # # If not, delete the file

    response = {"File to delete": filepath, "Status": 200}

    return response


@app.route('/')
def home():

    # Return a HTML template that describes how to use the interface?
    pass


if __name__ == '__main__':

    app.run(host='0.0.0.0', port='8000')
