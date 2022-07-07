"""Configures logging and starts the ``lasp_sdtp`` server

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be executed via the command line as such:
    ::
        python run_server.py
"""

from pathlib import Path

from lasp_sdtp.server.api import app
from lasp_sdtp.server.api import register_admin
from lasp_sdtp.config import admin_config
from lasp_sdtp.utils.utils import configure_logging

if __name__ == '__main__':

    # Configure logging
    log_file_loc = Path.home() / 'logs'
    configure_logging(log_file_loc)

    # Register an admin account if necessary
    register_admin()

    # Run the server
    app.run(host=admin_config['endpoint'], port='8000')
