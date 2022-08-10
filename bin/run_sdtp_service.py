"""This script configures logging and starts the ``sdtp_api`` ``flask`` server.

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
        python run_sdtp_service.py
"""

from pathlib import Path

from lasp_sdtp.server.sdtp_api import api_app
from lasp_sdtp.config import admin_config
from lasp_sdtp.utils.utils import configure_logging
from lasp_sdtp.utils.utils import register_admin


if __name__ == '__main__':

    # Configure logging
    log_file_loc = Path.home() / 'logs'
    configure_logging(log_file_loc)

    # Register an admin account if necessary
    register_admin()

    # Run the server
    api_app.run(host=admin_config['endpoint'], port=admin_config['sdtp_api_port'])
