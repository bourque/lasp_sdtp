"""The main module for running the ``last_sdtp`` flask application.

The ``flask`` server defined within serves as the main API for interacting
with the SDTP interface, and serves as an API gateway for the ``queue_api``
and ``request_api``.

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

import json
import logging

from flask import Flask
from flask import abort
from flask import make_response
from flask import request
from flask.wrappers import Response
import requests
from werkzeug import exceptions

from lasp_sdtp.config import admin_config
from lasp_sdtp.utils.utils import CustomJSONEncoder

logger = logging.getLogger(__name__)
api_app = Flask(__name__)
api_app.json_encoder = CustomJSONEncoder

REQUEST_API_URI = f'{admin_config["api_endpoint"]}:{admin_config["request_api_port"]}'
QUEUE_API_URI = f'{admin_config["api_endpoint"]}:{admin_config["queue_api_port"]}'


@api_app.before_request
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


@api_app.errorhandler(400)
def custom400(error: exceptions.BadRequest) -> Response:
    """Returns custom 400 response"""
    return make_response({'message': 'The request is incorrect'}, 400)


@api_app.errorhandler(401)
def custom401(error: exceptions.Unauthorized) -> Response:
    """Returns custom 401 response"""

    # The message depends on the request method
    if request.method == 'PUT':
        return make_response({'message': 'Unauthorized'}, 401)
    elif request.method == 'GET':
        return make_response({'message': 'Request is not authenticated'}, 401)


@api_app.errorhandler(404)
def custom404(error: exceptions.NotFound) -> Response:
    """Returns custom 400 response"""
    return make_response({'message': 'The requested resource does not exist'}, 404)


@api_app.route('/files/<fileid>', methods=['DELETE'])
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
        The response object containing appropriate headers and content.
    """

    # Send request to request API
    request_api_response = requests.delete(f'{REQUEST_API_URI}/delete_file/{fileid}')

    # If the request failed, abort
    if request_api_response.status_code == 400:
        abort(400)

    # Parse the response contents
    request_api_response = request_api_response.content.decode('utf-8')  # returns a str
    request_api_response = json.loads(request_api_response)  # Convert the str to a dict
    transactionid = int(request_api_response['transactionid'])

    # Send request to queue API
    queue_api_response = requests.delete(f'{QUEUE_API_URI}/delete_file/{fileid}')

    # If the request failed, abort
    if queue_api_response.status_code == 404:
        abort(404)

    # Construct the response
    content = {'message': 'Success but no other response necessary'}
    status = 204
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@api_app.route('/files/<fileid_start>-<fileid_end>', methods=['DELETE'])
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
        The response object containing appropriate headers and content.
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

    return api_app


@api_app.route('/files/<fileid>', methods=['GET'])
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
        The response object containing appropriate headers and content.
    """

    # Send request to request API
    request_api_response = requests.get(f'{REQUEST_API_URI}/get_file/{fileid}')\

    # If the request failed, abort
    if request_api_response.status_code in [400, 404]:
        abort(request_api_response.status_code)

    # Parse the response contents
    request_api_response = request_api_response.content.decode('utf-8')  # returns a str
    request_api_response = json.loads(request_api_response)  # Convert the str to a dict
    transactionid = int(request_api_response['transactionid'])

    # Send request to queue API
    queue_api_response = requests.get(f'{QUEUE_API_URI}/get_file/{fileid}').content.decode('utf-8')
    queue_api_response = json.loads(queue_api_response)
    filename = queue_api_response['filename']
    contents = queue_api_response['contents']

    # Construct the response
    content = {'filename': filename, 'contents': contents}
    status = 200
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@api_app.route('/files', methods=['GET'])
def get_filelist() -> Response:
    """Return a list of files available in the filesystem.

    Returns
    -------
    response : dict
        The response object containing appropriate headers and content.
    """

    # Parse the URL parameters
    params = request.query_string.decode('utf-8')
    request_api_url = f'{REQUEST_API_URI}/get_filelist'
    if params:
        request_api_url = f'{request_api_url}?{params}'

    # Send request to request API
    request_api_response = requests.get(request_api_url)

    # If the request failed, abort
    if request_api_response.status_code == 400:
        abort(400)

    # Parse the response contents
    request_api_response = request_api_response.content.decode('utf-8')  # returns a str
    request_api_response = json.loads(request_api_response)  # Convert the str to a dict
    results = request_api_response['results']
    transactionid = int(request_api_response['transactionid'])

    # Construct the response
    content = {'files': results}
    status = 200
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@api_app.route('/')
def home():
    """View for the homepage"""

    # Return a HTML template that describes how to use the interface?
    pass


@api_app.route('/register', methods=['PUT'])
def register() -> Response:
    """Register a subscriber and send the appropriate response back to the user

    Returns
    -------
    response : flask.wrappers.Response obj
        The response object containing appropriate headers and content.
    """

    # Send request to request API
    req_api_resp = requests.put(f'{REQUEST_API_URI}/register_subscriber').content.decode('utf-8')
    req_api_resp = json.loads(req_api_resp)
    transactionid = req_api_resp['transactionid']

    # Construct the response
    content = {'message': 'Success but no other response necessary'}
    status = 204
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response
