"""This script starts the ``queue_api`` ``flask`` server.

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be executed via the command line as such:
    ::
        python run_queue_service.py
"""

from lasp_sdtp.config import admin_config
from lasp_sdtp.server.queue_api import queue_app


if __name__ == '__main__':

    # Run the server
    queue_app.run(host=admin_config['endpoint'], port=admin_config['queue_api_port'])
