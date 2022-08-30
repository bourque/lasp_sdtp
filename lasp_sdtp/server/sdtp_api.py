"""This module serves as the main API for interacting with the ``lasp_sdtp``
application.

The ``flask`` server defined within contains views for each of the SDTP entry
points (i.e. ``PUT /register``, ``GET /files``, ``GET /files/<fileid>``, and
``DELETE /files/<fileid>``.  This API serves as a gateway for the ``queue_api``
(which handles the transferring of files and necessary bookkeeping) and the
``request_api`` (which records transactions, and parses, validates, and executes
requests.

Authors
-------
    Matthew Bourque

Use
---

    The ``flask`` server is intended to be run from the ``run_sdtp_service.py``
    script.  Once the server is running, the ``flask`` app will respond to
    requests to the ``endpoint`` and ``sdtp_api_port`` defined  in the
    ``admin_config.json`` file.

    To run a local server for development or testing purposes, use:
    ::
        FLASK_APP=sdtp_api.py FLASK_ENV=development flask run --port 8000

References
----------

    If asynchronous requests need to be supported in the future, this article
    provides some useful examples: https://testdriven.io/blog/flask-async/

TODO: Implement 403 errors (Request is authenticated but user is forbidden from
      accessing resource)
TODO: Implement parallelization for file transfers
TODO: Implement 429 errors (Too many requests)
TODO: Implement support for grouping files together
TODO: Implement support for pagination of GET /files requests
TODO: The JSON object returned in filelist request should have 'tags' as it's own key
TODO: Make sure DELETE requests are idempotent
"""

import logging

import requests
from flask import Flask
from flask import abort
from flask import make_response
from flask import request
from flask.wrappers import Response

from lasp_sdtp.config import admin_config
from lasp_sdtp.utils.utils import parse_api_response
from lasp_sdtp.utils.utils import validate_fileid_range

logger = logging.getLogger(__name__)
sdtp_api_app = Flask(__name__)

REQUEST_API_URI = f'{admin_config["api_endpoint"]}:{admin_config["request_api_port"]}'
QUEUE_API_URI = f'{admin_config["api_endpoint"]}:{admin_config["queue_api_port"]}'


@sdtp_api_app.route('/files/<fileid>', methods=['DELETE'])
def delete_file(fileid: int) -> Response:
    """Deletes the given file from the file queue, if applicable.

    A file is only deleted from the queue if it is not being used by any other
    subscriber.  If the file is deleted, the file transfer transaction is marked
    as 'complete' in the ``transactions`` database table, and the corresponding
    entry in the ``file_queue`` database table will be removed.

    If the file of interest doesn't exist, a 404 error is returned.  If the
    given ``fileid`` is invalid, a 400 error is returned.

    A successful request will result in a response of 204 ('Success but no other
    response necessary').

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest.

    Returns
    -------
    response : ``flask.wrappers.Response`` obj
        The response object containing appropriate headers and content.
    """

    # Send request to request API
    request_api_response = requests.delete(f'{REQUEST_API_URI}/delete_file/{fileid}')

    # If the request failed, abort
    if request_api_response.status_code == 400:
        abort(400)

    # Parse the response contents
    request_api_response = parse_api_response('request', request_api_response)
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


@sdtp_api_app.route('/files/<fileid_start>-<fileid_end>', methods=['DELETE'])
def delete_files(fileid_start: int, fileid_end: int) -> Response:
    """For a range of files, deletes those that are no longer needed from the
    file queue.

    This function essentially iterates through the range of ``fileid``s and
    sends a ``DELETE`` request for each ``fileid``. The combination of the given
    ``fileid_start`` and ``fileid_end`` must result in increasing positive
    integers.

    If the given range of ``fileid``s is invalid, a 400 error is returned.

    A successful request will result in a response of 204 ('Success but no other
    response necessary').

    Parameters
    ----------
    fileid_start : int
        The starting ``fileid`` of interest.
    fileid_end : int
        The ending ``fileid`` of interest.

    Returns
    -------
    response : ``flask.wrappers.Response`` obj
        The response object containing appropriate headers and content.
    """

    # Make sure range of fileids are valid
    valid = validate_fileid_range(fileid_start, fileid_end)
    if not valid:
        abort(400)

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


@sdtp_api_app.route('/files/<fileid>', methods=['GET'])
def get_file(fileid: int) -> Response:
    """Returns the contents of a given file.

    If the supplied ``fileid`` is not a valid positive integer, a 400 error is
    returned.  Also, if the file does not exist, a 404 error is returned.

    A successful request will result in the file being copied to the file
    queue, an entry being added the ``file_queue`` database table, and a
    response of 200 along with the contents of the file.

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest.

    Returns
    -------
    response : ``flask.wrappers.Response`` obj
        The response object containing appropriate headers and content.
    """

    # Send request to request API
    request_api_response = requests.get(f'{REQUEST_API_URI}/get_file/{fileid}')\

    # If the request failed, abort
    if request_api_response.status_code in [400, 404]:
        abort(request_api_response.status_code)

    # Parse the response contents
    request_api_response = parse_api_response('request', request_api_response)
    transactionid = int(request_api_response['transactionid'])

    # Send request to queue API
    queue_api_response = requests.get(f'{QUEUE_API_URI}/get_file/{fileid}')

    # Parse the response contents
    queue_api_response = parse_api_response('queue', queue_api_response)

    # Construct the response
    content = {'filename': queue_api_response['filename'], 'contents': queue_api_response['contents']}
    status = 200
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@sdtp_api_app.route('/files', methods=['GET'])
def get_filelist() -> Response:
    """Returns a list of files available in the filesystem.

    The user may supply parameters (i.e. 'tags') within the request
    (e.g. ``date=2021-01-01``). If parameters are given, they are parsed and
    applied to the query that determines the list of available files.  If no
    parameters are supplied, all available files are returned.

    If the request parameters are invalid, a 400 error is returned.

    A successful request will result in a response of 200 along with a list
    of available files and their metadata.

    Returns
    -------
    response : ``flask.wrappers.Response`` obj
        The response object containing appropriate headers and content.
    """

    # Parse the URL parameters
    params = request.query_string.decode('utf-8')
    request_api_url = f'{REQUEST_API_URI}/get_filelist'
    if params:
        request_api_url = f'{request_api_url}?{params}'

    # Send request to request API
    request_api_response = requests.get(request_api_url)

    # If the request failed with 400, abort
    if request_api_response.status_code == 400:
        abort(400)

    # Parse the response contents
    request_api_response = parse_api_response('request', request_api_response)
    results = request_api_response['results']
    transactionid = int(request_api_response['transactionid'])

    # Construct the response
    content = {'files': results}
    status = 200
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@sdtp_api_app.route('/register', methods=['PUT'])
def register() -> Response:
    """Registers a subscriber (if the subscriber's registration window is open).

    To establish a subscriber's registration window, an administrator should
    manually add an entry to the ``accounts`` database table for the subscriber
    and set the ``registration_open`` field to ``True``.

    Once the subscriber has registered the account via the ``PUT /register``
    request, the ``registration_open`` is set to ``False`` and the
    ``registration_expires`` field is set with the date of which the account
    registration will expire.

    If the subscriber attempts to register the account while the registration
    window is closed, or if a subscriber attempts to register an account that
    is not in the system, a 401 error is returned.

    A successful registration request will result in a response of 204 ('Success
    but no other response necessary').

    Returns
    -------
    response : ``flask.wrappers.Response`` obj
        The response object containing appropriate headers and content.
    """

    # Send request to request API
    request_api_response = requests.put(f'{REQUEST_API_URI}/register_subscriber')

    # If the request failed with 401, abort
    if request_api_response.status_code == 401:
        abort(401)

    # Parse the response contents
    request_api_response = parse_api_response('request', request_api_response)
    transactionid = request_api_response['transactionid']

    # Construct the response
    content = {'message': 'Success but no other response necessary'}
    status = 204
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response
