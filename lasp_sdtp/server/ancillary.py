"""Ancillary functions needed for ``lasp_sdtp`` server.

Authors
-------
    Matthew Bourque

Use
---

"""

from flask import abort
from flask import Flask
from flask import make_response
from flask import request
from flask.wrappers import Response
from werkzeug import exceptions

from lasp_sdtp.server.sdtp_api import api_app


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


@api_app.errorhandler(500)
def custom500(error: exceptions.InternalServerError) -> Response:
    """Returns custom 500 response"""
    return make_response({'message': 'Internal Server Error'}, 500)


def get_app() -> Flask:
    """Return an instance of the flask app (used for testing purposes)

    Returns
    -------
    app : flask.app.Flask obj
        An instance of the flask application
    """

    return api_app
