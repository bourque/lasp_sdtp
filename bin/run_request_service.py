"""This script starts the ``request_api`` ``flask`` server

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be executed via the command line as such:
    ::
        python run_server.py
"""

from lasp_sdtp.server.request_api import request_app
from lasp_sdtp.config import admin_config


if __name__ == '__main__':

    # Run the servers
    request_app.run(host=admin_config['endpoint'], port=admin_config['request_api_port'])
