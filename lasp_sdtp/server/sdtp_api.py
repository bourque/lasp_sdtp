"""This module serves as the main API for interacting with the ``lasp_sdtp``
application.

The ``flask`` server defined within contains views for each of the SDTP entry
points (i.e. ``PUT /register``, ``GET /files``, ``GET /files/<fileid>``, and
``DELETE /files/<fileid>``.  This API serves as a gateway for the ``queue_api``
(which handles the transferring of files and necessary bookkeeping) and the
``request_api`` (which records transactions, and parses, validates, and executes
requests).

Authors
-------
    - Matthew Bourque

Example
-------

    To run a local server for development or testing purposes, use:
    ::
        FLASK_APP=sdtp_api.py FLASK_ENV=development flask run --port 8000

References
----------

    If asynchronous requests need to be supported in the future, this article
    provides some useful examples: https://testdriven.io/blog/flask-async/

TODO[TIMDS-1991]: Implement parallelization for file transfers
TODO[TIMDS-1992]: Implement 429 errors (Too many requests)
TODO[TIMDS-1993]: Implement support for grouping files together
TODO[TIMDS-1994]: Make diagram of how a file flows through the system
TODO[TIMDS-1995]: Add logic to update transactions.responseStatus field
TODO: Add 'finally' clause where it makes sense
"""

import logging
import socket

import requests
from flask import Flask
from flask import abort
from flask import make_response
from flask import request
from flask.wrappers import Response
from werkzeug import exceptions

from lasp_sdtp.config import admin_config
from lasp_sdtp.database.cleanup import cleanup_files
from lasp_sdtp.utils.logging import configure_logging
from lasp_sdtp.utils.utils import parse_api_response
from lasp_sdtp.utils.utils import validate_fileid_range

sdtp_app = Flask(__name__)

if 'MacL' in socket.gethostname():  # running locally
    REQUEST_API_URI = f'http://127.0.0.1:{admin_config["request_api_port"]}'
    QUEUE_API_URI = f'http://127.0.0.1:{admin_config["queue_api_port"]}'
else:   # running in docker container
    REQUEST_API_URI = f'http://request_api:{admin_config["request_api_port"]}'
    QUEUE_API_URI = f'http://queue_api:{admin_config["queue_api_port"]}'
    # Configure logging
    log_file_loc = '/root/logs/'
    configure_logging(log_file_loc)

logger = logging.getLogger(__name__)

@sdtp_app.before_request
def authorize():
    """Authorize a request.

    This is performed before every request is processed.  If the request cannot
    be authorized, the request is aborted with a 401 error.
    """

    # Assume user is not authorized until proven otherwise
    #valid_certificate = False

    # Temporary work-around
    # Write request to a file so it can be checked
    logger.info('Received request:')
    logger.info(str(request.headers.__dict__['environ']))

    valid_certificate = True

    # Check for a valid certificate in the header
    # if 'Cert-UID' in request.headers:
    #     certificate = request.headers['Cert-UID']
    #     authorized_certificates = ['ges_disc_cert', 'test_account_cert']  # Probably better to do a db lookup here?
    #     if certificate in authorized_certificates:
    #         valid_certificate = True

    if not valid_certificate:
        abort(401)


@sdtp_app.errorhandler(400)
def custom400(error: exceptions.BadRequest) -> Response:
    """Returns a custom 400 response"""
    return make_response({'message': 'The request is incorrect'}, 400)


@sdtp_app.errorhandler(401)
def custom401(error: exceptions.Unauthorized) -> Response:
    """Returns a custom 401 response"""

    # The message depends on the request method
    if request.method == 'PUT':
        return make_response({'message': 'Unauthorized'}, 401)
    elif request.method == 'GET':
        return make_response({'message': 'Request is not authenticated'}, 401)


@sdtp_app.errorhandler(403)
def custom403(error: exceptions.Forbidden) -> Response:
    """Returns a custom 403 response"""
    return make_response({'message': 'Request is authenticated but user is forbidden from accessing resource'}, 403)


@sdtp_app.errorhandler(404)
def custom404(error: exceptions.NotFound) -> Response:
    """Returns a custom 400 response"""
    return make_response({'message': 'The requested resource does not exist'}, 404)


@sdtp_app.errorhandler(500)
def custom500(error: exceptions.InternalServerError) -> Response:
    """Returns a custom 500 response"""
    return make_response({'message': 'Internal Server Error'}, 500)


@sdtp_app.route('/files/<fileid>', methods=['DELETE'])
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

    logger.info('Received request to delete file %s', fileid)

    # Send request to request API
    logger.debug('Sending request to request API')
    request_api_response = requests.delete(f'{REQUEST_API_URI}/delete_file/{fileid}')

    # If the request failed, abort
    if request_api_response.status_code in [400, 403, 404]:
        logger.critical('Request has failed with code %s', request_api_response.status_code)
        abort(request_api_response.status_code)

    # Parse the response contents
    logger.debug('Parsing request API response')
    request_api_response = parse_api_response('request', request_api_response)
    transactionid = int(request_api_response['transactionid'])

    # Send request to queue API
    logger.debug('Sending request to queue API')
    queue_api_response = requests.delete(f'{QUEUE_API_URI}/delete_file/{fileid}')

    # If the request failed, abort
    if queue_api_response.status_code == 404:
        logger.critical('Request has failed with code 404')
        abort(404)

    # Construct the response
    logger.debug('Constructing response')
    content = {'message': 'Success but no other response necessary'}
    status = 204
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@sdtp_app.route('/files/<fileid_start>-<fileid_end>', methods=['DELETE'])
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

    logger.info('Received request to delete files %s-%s', fileid_start, fileid_end)

    # Make sure range of fileids are valid
    logger.debug('Validating fileids')
    valid = validate_fileid_range(fileid_start, fileid_end)
    if not valid:
        logger.critical('The given fileid range is not valid. Aborting with status code 400')
        abort(400)

    # Iterate through the files and delete them individually
    fileids = [fileid for fileid in range(int(fileid_start), int(fileid_end) + 1)]
    for fileid in fileids:
        logger.debug('Deleting file %s', fileid)
        delete_file(fileid)

    # Construct the response
    logger.debug('Constructing response')
    content = {'message': 'Success but no other response necessary'}
    status = 204
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'

    return response


@sdtp_app.route('/files/<fileid>', methods=['GET'])
def get_file(fileid: int) -> Response:
    """Returns the contents of a given file.

    If the supplied ``fileid`` is not a valid positive integer, a 400 error is
    returned.  Also, if the file does not exist, a 404 error is returned.

    A successful request will result in the file being copied to the subscriber
    queue staging area, an entry being added the ``file_queue`` database table,
    and a response of 200 along with the contents of the file.

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest.

    Returns
    -------
    response : ``flask.wrappers.Response`` obj
        The response object containing appropriate headers and content.
    """

    logger.info('Received request to get file %s', fileid)

    # Send request to request API
    logger.debug('Sending request to request API')
    request_api_response = requests.get(f'{REQUEST_API_URI}/get_file/{fileid}')\

    # If the request failed, abort
    if request_api_response.status_code in [400, 403, 404]:
        logger.critical('Request has failed with code %s', request_api_response.status_code)
        abort(request_api_response.status_code)

    # Parse the response contents
    logger.debug('Parsing request API response')
    request_api_response = parse_api_response('request', request_api_response)
    transactionid = int(request_api_response['transactionid'])

    # Send request to queue API
    logger.debug('Sending request to queue API')
    queue_api_response = requests.get(f'{QUEUE_API_URI}/get_file/{fileid}')

    # Parse the response contents
    logger.debug('Parsing queue API response')
    queue_api_response = parse_api_response('queue', queue_api_response)

    # Construct the response
    logger.debug('Constructing response')
    content = {'filename': queue_api_response['filename'], 'contents': queue_api_response['contents']}
    status = 200
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@sdtp_app.route('/files', methods=['GET'])
def get_filelist() -> Response:
    """Returns a list of files available to the subscriber for file transfer.

    The user may supply parameters (i.e. 'tags') within the request
    (e.g. ``shortname=TSIS2_L1``). If parameters are given, they are parsed and
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

    logger.info('Received request to get filelist')

    # Parse the URL parameters
    params = request.query_string.decode('utf-8')
    request_api_url = f'{REQUEST_API_URI}/get_filelist'
    if params:
        request_api_url = f'{request_api_url}?{params}'

    # Send request to request API
    logger.debug('Sending request to request API')
    request_api_response = requests.get(request_api_url)

    # If the request failed with 400, abort
    if request_api_response.status_code == 400:
        logger.critical('Request has failed with code 400')
        abort(400)

    # Parse the response contents
    logger.debug('Parsing request API response')
    request_api_response = parse_api_response('request', request_api_response)
    results = request_api_response['results']
    transactionid = int(request_api_response['transactionid'])

    # Construct the response
    logger.debug('Constructing response')
    content = {'files': results}
    status = 200
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@sdtp_app.route('/register', methods=['PUT'])
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

    logger.info('Received request to register subscriber')

    # Send request to request API
    logger.debug('Sending request to request API')
    request_api_response = requests.put(f'{REQUEST_API_URI}/register_subscriber')

    # If the request failed with 401, abort
    if request_api_response.status_code == 401:
        logger.critical('Request has failed with code 401')
        abort(401)

    # Parse the response contents
    logger.debug('Parsing request API response')
    request_api_response = parse_api_response('request', request_api_response)
    transactionid = request_api_response['transactionid']

    # Construct the response
    logger.debug('Constructing response')
    content = {'message': 'Success but no other response necessary'}
    status = 204
    response = make_response(content, status)
    response.headers['Content-Type'] = 'application/json'
    response.headers['SDTP-TransactionID'] = transactionid

    return response


@sdtp_app.before_request
def remove_expired_data():
    """Remove expired files from the database prior to processing a request in
    order to avoid allowing inadvertent access.
    """

    cleanup_files()