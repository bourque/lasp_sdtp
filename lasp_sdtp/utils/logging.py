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
import getpass
import importlib
import logging
import logging.config
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


def _get_log_config(log_file: str) -> dict:
    """Define and return the logging configuration.

    Parameters
    ----------
    log_file : str
        The path to the log file

    Returns
    -------
    log_config : dict
        The logging configuration
    """

    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'class': 'logging.Formatter',
                'format': '[%(asctime)s] %(message)s',
                'datefmt': '%Y-%m-%dT%H:%M:%S'
            },
            'detailed': {
                'class': 'logging.Formatter',
                'format': '[%(asctime)s %(name)s.%(funcName)s:%(lineno)i %(levelname)s] %(message)s',
                'datefmt': '%Y-%m-%dT%H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': str(log_file),
                'mode': 'a'
            }
        },
        'loggers': {
            'lasp_sdtp': {
                'level': 'DEBUG'
            },
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console', 'file']
        }
    }

    return log_config


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
    logging.debug(f'User: {getpass.getuser()}')
    logging.debug(f'System: {socket.gethostname()}')
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
            mod = importlib.import_module(dependency)
            logging.debug(f'{dependency} Version: {mod.__version__}')
            logging.debug(f'{dependency} Path: {mod.__path__[0]}')
        except (ImportError, AttributeError) as error:
            logging.warning(error)

    # Log environment information
    environment = subprocess.check_output(['conda', 'env', 'export'], universal_newlines=True)
    logging.debug('Conda Environment:')
    for line in environment.split('\n'):
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

    # Define the log configuration
    log_config = _get_log_config(log_file)

    # Configure the log
    logging.Formatter.converter = time.gmtime  # Timestamps are in UTC
    logging.config.dictConfig(log_config)
    if verbose:
        print('Log file initialized to {}'.format(log_file))

    # Log system configuration/environment
    _log_system_environment()

    return log_file
