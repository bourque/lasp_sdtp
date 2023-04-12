"""Various functions to configure and perform system logging.

Authors
-------
    Matthew Bourque

Use
---
    Functions within this module are intended to be imported and used within
    the ``run_sdtp_service.py`` script:
    ::
        from lasp_sdtp.utils.logging import configure_logging

References
----------

    Logging configuration was inspired by ``tsis_disc``:
    (https://bitbucket.lasp.colorado.edu/users/brst3037/repos/tsis_disc/browse/scripts/process_to_lasp.py)
"""

import datetime
import logging
import logging.config
import subprocess
import sys
import time
from getpass import getuser
from importlib import import_module
from pathlib import Path
from socket import gethostname
from typing import Optional

from lasp_sdtp.utils.properties import LOG_CONFIG


def _get_log_file(log_file_loc: str) -> str:
    """Define filename/filepath for log file and create the necessary
    directories to store it.

    Returns
    -------
    log_file : str
        The path to the file where the log is written to.
    """

    # Define filename for log file
    timestamp = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    filename = f'lasp_sdtp_{timestamp}.log'
    log_file = Path(log_file_loc) / filename

    # Make sure parent directory exists
    log_file.parent.mkdir(exist_ok=True)

    return log_file


def _log_system_environment():
    """Log various system and software environment information, which may help
    with debugging."""

    # Log system information
    python_version = sys.version.replace("\n", "")
    logging.debug(f'User: {getuser()}')
    logging.debug(f'System: {gethostname()}')
    logging.debug(f'Python Version: {python_version}')
    logging.debug(f'Python Executable Path: {sys.executable}')

    # Get list of dependencies
    setup_file = Path(__file__).parents[2] / 'setup.cfg'
    with open(setup_file, 'r') as f:
        data = f.readlines()
    for i, line in enumerate(data):
        if 'install_requires =' in line:
            begin = i + 1
        elif 'python_requires =' in line:
            end = i - 1
    dependencies = data[begin:end]
    dependencies = [item.strip().replace("'", "").replace(',', '').split('=')[0].split('>')[0].split('<')[0] for item in dependencies]

    # Log dependency versions and paths
    for dependency in dependencies:
        try:
            mod = import_module(dependency)
            logging.debug(f'{dependency} Version: {mod.__version__}')
            logging.debug(f'{dependency} Path: {mod.__path__[0]}')
        except (ImportError, AttributeError) as error:
            logging.warning(error)

    # Log poetry environment information
    logging.debug('Poetry Environment:')
    poetry_environment = subprocess.check_output(['poetry', 'env', 'info'], universal_newlines=True)
    for line in poetry_environment.split('\n'):
        logging.debug(f'\t{line}')

    # Log poetry environment dependencies
    logging.debug('Poetry Dependencies:')
    poetry_dependencies = subprocess.check_output(['poetry', 'show'], universal_newlines=True)
    for line in poetry_dependencies.split('\n'):
        logging.debug(f'\t{line}')


def configure_logging(log_file_loc: str, verbose: Optional[bool] = True) -> str:
    """Configure and create a log that records system information.

    Parameters
    ----------
    log_file_loc : str
        The parent directory in which to save the log file
    verbose : boolean
        Switches on/off printing information to stdout

    Returns
    -------
    log_file : str
        The path to the file where the log is written to.
    """

    # Define where the log file will be stored
    log_file = _get_log_file(log_file_loc)
    LOG_CONFIG['handlers']['file']['filename'] = str(log_file)

    # Configure the log
    logging.Formatter.converter = time.gmtime  # Timestamps are in UTC
    logging.config.dictConfig(LOG_CONFIG)
    if verbose:
        print('Log file initialized to {}'.format(str(log_file)))

    # Log system configuration/environment
    _log_system_environment()

    return log_file
