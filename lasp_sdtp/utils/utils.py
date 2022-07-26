"""Various utility functions to help support the ``lasp_sdtp`` application

Authors
-------
    Matthew Bourque

Use
---
    Functions within this module are intended to be imported and used within
    other modules, e.g.:
    ::
        from lasp_sdtp.utils.utils import get_checksum

TODO: Figure out how information for subscriber-supplied tags/extras should be
      stored/provided
"""

import datetime
import getpass
import importlib
import json
import logging
import random
import socket
import string
import subprocess
import sys
import time
from pathlib import Path

from flask import abort
from flask.json import JSONEncoder
from flask.wrappers import Response

from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db

logger = logging.getLogger(__name__)


class CustomJSONEncoder(JSONEncoder):
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


def configure_logging(log_file_loc: str, verbose=True) -> str:
    """Create and configure a log file with a standard logging format.

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

    # Build filename
    timestamp = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    filename = f'lasp_sdtp_{timestamp}.log'
    log_file = Path(log_file_loc) / filename

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


def get_checksum() -> str:
    """Return a randomly generated checksum.  Currently, only supports the
    ``sha256`` checksum type.

    Returns
    -------
    checksum : str
        A randomly generated checksum based on the ``checksum_type`` given in
        the system configuration
    """

    checksum_type = subscriber_config['checksum_type']
    checksum_string = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(64))
    checksum = f'{checksum_type}:{checksum_string}'

    return checksum


def get_shortname(filename: str) -> str:
    """Return the appropriate value for the ``ShortName`` tag for the given
    filename.  Currently, this is hard-coded to only support TSIS-2.

    Parameters
    ----------
    filename : str
        The filename of interest (e.g. ``tsis2_tim_L2_v01_20220422.zip``)

    Returns
    -------
    shortname : str
        The ``ShortName`` that matches the given filename (e.g.
        ``TSIS2_TIM_L2``)
    """

    shortname_mapping = {
        'tsis2_L1': 'TSIS2_L1',
        'tsis2_sim_cal': 'TSIS2_SIM_CAL',
        'tsis2_tim_cal': 'TSIS2_TIM_CAL',
        'tsis2_sim_L2': 'TSIS2_SIM_L2',
        'tsis2_tim_L2': 'TSIS2_TIM_L2',
        'tsis2_sc_L2': 'TSIS_SC_L2',
        'tsis2_ssi_L3_c12h': 'TSIS2_SSI_L3_12HR',
        'tsis2_ssi_L3_c24h': 'TSIS2_SSI_L3_24HR',
        'tsis2_tsi_L3_c06h': 'TSIS2_TSI_L3_06HR',
        'tsis2_tsi_L3_c24h': 'TSIS2_TSI_L3_24HR'
    }

    for item in shortname_mapping:
        if filename.startswith(item):
            shortname = shortname_mapping[item]
            if filename.endswith('.txt'):
                shortname += '_TXT'
            elif filename.endswith('.nc'):
                shortname += '_NC'

    return shortname


def parse_api_response(api: str, response: Response) -> dict:
    """
    """

    try:
        response = json.loads(response.content.decode('utf-8'))
    except json.JSONDecodeError:
        logger.critical('Problem with response from %s API' % api)
        abort(500)

    return response


def parse_request_tags(request: object) -> dict:
    """Parse the tags in the request and store them in a dictionary.  If any
    unsupported tags are encountered, a 404 error is raised.

    Parameters
    ----------
    request : obj
        The request to parse

    Returns
    -------
    tags : dict
        A dictionary of key/value pairs for the request tags
    """

    # Define the default supported tags
    default_tag_list = [
        ('stream', 'prod', str),
        ('ShortName', 'all', str),
        ('version', 'v01', str),
        ('date', None, str),
        ('start_date', None, str),
        ('end_date', None, str)]

    # Parse the subscriber-defined tags
    subscriber_tags = subscriber_config['tags']
    subscriber_tag_list = []
    for tag in subscriber_tags:
        subscriber_tag_list.append((tag, subscriber_tags[tag]['default'], eval(subscriber_tags[tag]['type'])))

    # Supported tags is an aggregation of the default + subscriber-defined tags
    supported_tags = default_tag_list + subscriber_tag_list

    # Check to see if any of the provided tags in the request are not supported
    for item in request.args.keys():
        if item not in [item[0] for item in supported_tags]:
            abort(400)

    # Store tags from request in a dictionary
    tags = {}
    for item in supported_tags:
        tags[item[0].lower()] = request.args.get(item[0], default=item[1], type=item[2])

    return tags


def register_admin():
    """Registers an ``admin`` account if it doesn't already exist"""

    # Check if an admin account already exists
    account = db.query_for_account('lasp_admin')

    # If it doesn't, create one
    if not account:
        data = [{
            'username': 'lasp_admin',
            'certuid': 'admin_cert',
            'role': 'admin',
            'registration_date': datetime.datetime.utcnow().date()}]
        db.insert_data('accounts', data)
        logger.info('Registered admin account')


def validate_fileid(fileid: str) -> bool:
    """Make sure that the provided ``fileid`` is a positive integer that is 15
    digits or fewer.  If it is not, a 400 error is raised.

    Parameters
    ----------
    fileid : str
        The ``fileid`` given in the request
    Returns
    -------
    bool
        True or False for whether or not the ``fileid`` is valid
    """

    # Make sure given fileid is an integer
    try:
        int(fileid)
    except ValueError:
        return False

    # Make sure the given fileid is a positive integer that is 15 digits or less
    if int(fileid) <= 0 or int(fileid) > 999999999999999:
        return False
    else:
        return True


def validate_tags(tags: dict) -> bool:
    """Make sure that all the provided tags are of valid type and value.  If
    any of them are not, a 404 error is raised.

    Parameters
    ----------
    tags : dict
        A dictionary of key/value pairs for the request tags

    Returns
    -------
    bool
        True or False for whether or not the tags are valid
    """

    # Make sure the date/start_date/end_date combination is valid
    # e.g. if a date is provided, the start and end dates should be None
    date_types = (type(tags['date']), type(tags['start_date']), type(tags['end_date']))
    valid_date_type_combos = [(type(None), type(None), type(None)), (str, type(None), type(None)), (type(None), str, str)]
    if date_types not in valid_date_type_combos:
        return False
    else:
        return True
