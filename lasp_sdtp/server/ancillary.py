"""Ancillary functions needed for the application servers.

These functions are not necessarily tied to a specific API and thus they are
grouped together in this module.  Most of the functions within serve as
request handlers and thus are automatically invoked (depending on the request)
and therefore do not need to be imported in the APIs.

Authors
-------
    Matthew Bourque
"""

from flask import abort
from flask import Flask
from flask import make_response
from flask import request
from flask.wrappers import Response
from werkzeug import exceptions

from lasp_sdtp.server.sdtp_api import sdtp_api_app


@sdtp_api_app.before_request
def authorize():
    """Authorize a request.

    This is performed before every request is processed.  If the request cannot
    be authorized, the request is aborted with a 401 error.
    """

    # Assume user is not authorized until proven otherwise
    valid_certificate = False

    # Check for a valid certificate in the header
    if 'Cert-UID' in request.headers:
        certificate = request.headers['Cert-UID']
        authorized_certificates = ['ges_disc_cert', 'test_account_cert']  # Probably better to do a db lookup here?
        if certificate in authorized_certificates:
            valid_certificate = True

    if not valid_certificate:
        abort(401)


@sdtp_api_app.errorhandler(400)
def custom400(error: exceptions.BadRequest) -> Response:
    """Returns a custom 400 response"""
    return make_response({'message': 'The request is incorrect'}, 400)


@sdtp_api_app.errorhandler(401)
def custom401(error: exceptions.Unauthorized) -> Response:
    """Returns a custom 401 response"""

    # The message depends on the request method
    if request.method == 'PUT':
        return make_response({'message': 'Unauthorized'}, 401)
    elif request.method == 'GET':
        return make_response({'message': 'Request is not authenticated'}, 401)


@sdtp_api_app.errorhandler(403)
def custom403(error: exceptions.Forbidden) -> Response:
    """Returns a custom 403 response"""
    return make_response({'message': 'Request is authenticated but user is forbidden from accessing resource'}, 403)


@sdtp_api_app.errorhandler(404)
def custom404(error: exceptions.NotFound) -> Response:
    """Returns a custom 400 response"""
    return make_response({'message': 'The requested resource does not exist'}, 404)


@sdtp_api_app.errorhandler(500)
def custom500(error: exceptions.InternalServerError) -> Response:
    """Returns a custom 500 response"""
    return make_response({'message': 'Internal Server Error'}, 500)


def get_app() -> Flask:
    """Return an instance of the flask app (used for testing purposes)

    Returns
    -------
    api_app : ``flask.app.Flask`` object
        An instance of the ``sdtp_api`` ``flask`` application
    """

    return sdtp_api_app
