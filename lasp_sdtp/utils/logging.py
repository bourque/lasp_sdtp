"""Various functions to enable system logging for the ``lasp_sdtp`` application

Authors
-------
    Matthew Bourque

Use
---
    Functions within this module are intended to be imported and used within
    other modules, e.g.:
    ::
        from lasp_sdtp.utils.logging import configure_logging
"""

import datetime
import getpass
import importlib
import logging
import socket
import subprocess
import sys
import os

HOME_DIR = os.path.join(os.path.expanduser('~'), 'Desktop')


def configure_logging():
    """Create and configure a log file with a standard logging format.

    Returns
    -------
    log_file : str
        The path to the file where the log is written to.
    """

    # Build filename
    timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    filename = f'lasp_sdtp_{timestamp}.log'
    log_file = os.path.join(HOME_DIR, 'logs', filename)

    # Make sure parent directory exists
    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file))

    # Make sure no other root handlers exist before configuring the logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create the log file
    logging.basicConfig(filename=log_file, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%m/%d/%Y %H:%M:%S %p', level=logging.INFO)
    print('Log file initialized to {}'.format(log_file))

    # Log system information
    python_version = sys.version.replace("\n", "")
    logging.info(f'User: {getpass.getuser()}')
    logging.info(f'System: {socket.gethostname()}')
    logging.info(f'Python Version: {python_version}')
    logging.info(f'Python Executable Path: {sys.executable}')

    # Get list of dependencies
    setup_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'setup.py')
    with open(setup_file, 'r') as f:
        data = f.readlines()
    for i, line in enumerate(data):
        if 'REQUIRES = [' in line:
            begin = i + 1
        elif 'setup(' in line:
            end = i - 2
    dependencies = data[begin:end]
    dependencies = [item.strip().replace("'", "").replace(',', '').split('=')[0].split('>')[0].split('<')[0] for item in dependencies]

    # Log dependency versions and paths
    for dependency in dependencies:
        try:
            mod = importlib.import_module(dependency)
            logging.info(f'{dependency} Version: {mod.__version__}')
            logging.info(f'{dependency} Path: {mod.__path__[0]}')
        except (ImportError, AttributeError) as error:
            logging.warning(error)

    # Log environment information
    environment = subprocess.check_output(['conda', 'env', 'export'], universal_newlines=True)
    logging.info('Conda Environment:')
    for line in environment.split('\n'):
        logging.info(f'\t{line}')

    return log_file
