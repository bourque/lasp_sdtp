"""Various functions to enable system logging for the ``lasp_sdtp`` application

Authors
-------
    Matthew Bourque

Use
---
    Functions within this module are intended to be imported and used within
    other modules, e.g.:
    ::
        from lasp_sdtp.utils.logging import configure
"""

import datetime
import getpass
import importlib
import logging
import socket
import subprocess
import sys
import time
from pathlib import Path

HOME_DIR = Path.home() / 'Desktop'

def configure(verbose=True) -> str:
    """Create and configure a log file with a standard logging format.

    Parameters
    ----------
    verbose : boolean
        Switches on/off printing information to stdout

    Returns
    -------
    log_file : str
        The path to the file where the log is written to.
    """

    # Build filename
    timestamp = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    filename = f'lasp_sdtp_{timestamp}.log'
    log_file = HOME_DIR / 'logs' / filename

    # Make sure parent directory exists
    log_file.parent.mkdir(exist_ok=True)

    # Make sure no other root handlers exist before configuring the logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create the log file
    logging.Formatter.converter = time.gmtime  # Timestamps are in UTC
    logging.basicConfig(filename=log_file, format='%(asctime)s.%(msecs)03d %(levelname)s: %(message)s', datefmt='%Y-%m-%dT%H:%M:%S', level=logging.DEBUG)
    if verbose:
        print('Log file initialized to {}'.format(log_file))

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

    return log_file
