"""This script configures logging and starts the flask servers for the SDTP
application

Also, when executed, an ``lasp_admin`` account is registered, if it doesn't
already exist.

The server is run from the ``endpoint`` defined in the ``admin_config.json``
file.  A log file is also created, the path to which will be printed to the
terminal.

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be executed via the command line as such:
    ::
        python run_sdtp_servers.py
"""

import threading

from lasp_sdtp.config import admin_config
from lasp_sdtp.server.api_utils import register_admin
from lasp_sdtp.server.queue_api import queue_app
from lasp_sdtp.server.request_api import request_app
from lasp_sdtp.server.sdtp_api import sdtp_app


def run_queue_app():
    queue_app.run(host=admin_config['endpoint'], port=admin_config['queue_api_port'], threaded=True)


def run_request_app():
    request_app.run(host=admin_config['endpoint'], port=admin_config['request_api_port'], threaded=True)


def run_sdtp_app():
    sdtp_app.run(host=admin_config['endpoint'], port=admin_config['sdtp_api_port'], threaded=True)


if __name__ == '__main__':

    # Register an admin account if necessary
    register_admin()

    # Run the servers
    t1 = threading.Thread(target=run_sdtp_app)
    t2 = threading.Thread(target=run_request_app)
    t3 = threading.Thread(target=run_queue_app)
    t1.start()
    t2.start()
    t3.start()
