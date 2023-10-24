"""Various non-API-specific functions needed to support the application servers.

These functions are not necessarily tied to a specific API and thus they are
grouped together in this module.

Authors
-------
    - Matthew Bourque
"""

import datetime
import logging

from flask import Flask
from flask.json import JSONEncoder

from lasp_sdtp.server.sdtp_api import sdtp_app
from lasp_sdtp.database.controller import db
from lasp_sdtp.database.queries import query_for_account_by_username

logger = logging.getLogger(__name__)


class CustomJSONEncoder(JSONEncoder):
    """Defines a custom JSON encoder that allows responses from requests sent
    via ``curl`` to contain datetime formats of ``YYYY-MM-DD`` instead of the
    default timestamp format (e.g. ``Thu, 06 Jan 2022 00:00:00 GMT``).
    """
    def default(self, obj):
        try:
            if isinstance(obj, datetime.date):
                return obj.isoformat().split('T')[0]
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


def get_app() -> Flask:
    """Return an instance of the flask app (used for testing purposes)

    Returns
    -------
    api_app : ``flask.app.Flask`` object
        An instance of the ``sdtp_api`` ``flask`` application
    """

    return sdtp_app


def register_admin():
    """Registers an ``admin`` account if it doesn't already exist"""

    # Check if an admin account already exists
    account = query_for_account_by_username('lasp_admin')

    # If it doesn't, create one
    if not account:
        data = [db.Accounts(
            username='lasp_admin',
            role='admin',
            registration_open=False,
            certuid='admin_cert',
            registration_date=datetime.datetime.utcnow().date())]
        db.insert_data(data)
        logger.info('Registered admin account')
