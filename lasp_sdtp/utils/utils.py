"""Various utility functions to help support the ``lasp_sdtp`` application.

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
TODO: Make create_test_filesystem and get_shortname to be more generic, avoid
      hard references to TSIS-2
"""

import datetime
import json
import logging
import random
import string
from pathlib import Path

from flask import abort
from flask.json import JSONEncoder
from flask.wrappers import Response

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.database_controller import db

logger = logging.getLogger(__name__)


class CustomJSONEncoder(JSONEncoder):
    """Defines a custom JSON encoder that allows responses from requests sent
    via ``curl`` to contain datetime formats of ``YYYY-MM-DD`` instead of the
    default timestamp format (e.g. ``Thu, 06 Jan 2022 00:00:00 GMT``).
    """
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


def create_test_filesystem():
    """Create a small, local filesystem of files used for testing purposes.

    The filesystem is stored in the directory defined by the ``filesystem_loc``
    key in the ``admin_config.json`` file.
    """

    # Create parent directory for storing test files
    test_directory = Path(admin_config['filesystem_loc']) / 'prod'
    test_directory.mkdir(parents=True, exist_ok=True)

    filename_structures = {
        'TSIS2_L1': 'tsis2_L1_<date>.zip',
        'TSIS2_SIM_CAL': 'tsis2_sim_cal_v01.zip',
        'TSIS2_TIM_CAL': 'tsis2_tim_cal_v01.zip',
        'TSIS2_SIM_L2': 'tsis2_sim_L2_v01_<date>.zip',
        'TSIS2_TIM_L2': 'tsis2_tim_L2_v01_<date>.zip',
        'TSIS2_SC_L2': 'tsis2_sc_L2_v01_<date>_<date2>.zip',
        'TSIS2_SSI_L3_12HR_TXT': 'tsis2_ssi_L3_c12h_v01_<date>_<date2>.txt',
        'TSIS2_SSI_L3_24HR_TXT': 'tsis2_ssi_L3_c24h_v01_<date>_<date2>.txt',
        'TSIS2_TSI_L3_06HR_TXT': 'tsis2_tsi_L3_c06h_v01_<date>_<date2>.txt',
        'TSIS2_TSI_L3_24HR_TXT': 'tsis2_tsi_L3_c24h_v01_<date>_<date2>.txt',
        'TSIS2_SSI_L3_12HR_NC': 'tsis2_ssi_L3_c12h_v01_<date>_<date2>.nc',
        'TSIS2_SSI_L3_24HR_NC': 'tsis2_ssi_L3_c12h_v01_<date>_<date2>.nc',
        'TSIS2_TSI_L3_06HR_NC': 'tsis2_tsi_L3_c06h_v01_<date>_<date2>.nc',
        'TSIS2_TSI_L3_24HR_NC': 'tsis2_tsi_L3_c24h_v01_<date>_<date2>.nc'
    }

    for shortname in filename_structures:

        # Create files for five different days
        dates = ['20220101', '20220102', '20220103', '20220104', '20220105']
        for date in dates:
            base_filename = filename_structures[shortname]
            base_filename = base_filename.replace('<date>', date)
            if '<date2>' in base_filename:
                next_day = datetime.datetime.strftime(datetime.datetime.strptime(date, '%Y%m%d') + datetime.timedelta(days=1), '%Y%m%d')
                base_filename = base_filename.replace('<date2>', next_day)

            filename = test_directory / base_filename
            with open(filename, 'w') as f:
                f.write(f'File contents for {filename.name}')
            print(f'Created test file: {filename}')


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
    """Parse a response from the given API.

    If the response cannot be parsed into a dictionary/JSON-like object,
    then a 500 error is returned.

    Parameters
    ----------
    api : str
        The API that the response came from (can be either ``request`` or
        ``queue``)
    response : ``flask.wrappers.Response`` obj
        The response object to parse

    Returns
    -------
    response : dict
        The parsed response, now a decoded dict
    """

    try:
        response = json.loads(response.content.decode('utf-8'))
    except json.JSONDecodeError:
        logger.critical('Problem with response from %s API' % api)
        abort(500)

    return response


def parse_request_parameters(request: object) -> dict:
    """Parse the parameters in the request and store them in a dictionary.  If
    any unsupported parameters are encountered, a 400 error is raised.

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

    # # Parse the subscriber-defined tags
    # subscriber_tags = subscriber_config['tags']
    # subscriber_tag_list = []
    # for tag in subscriber_tags:
    #     subscriber_tag_list.append((tag, subscriber_tags[tag]['default'], eval(subscriber_tags[tag]['type'])))
    subscriber_tag_list = []  # TODO: Add support for user-defined tags

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
            'role': 'admin',
            'registration_open': False,
            'certuid': 'admin_cert',
            'registration_date': datetime.datetime.utcnow().date()}]
        db.insert_data('accounts', data)
        logger.info('Registered admin account')


def validate_fileid(fileid: str) -> bool:
    """Check that the provided ``fileid`` is a positive integer that is 15
    digits or fewer.

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


def validate_fileid_range(fileid_start: int, fileid_end: int) -> bool:
    """Make sure that the provided range of ``fileid``s are positive integers
    that are increasing in value.

    Parameters
    ----------
    fileid_start : int
        The starting ``fileid`` of interest.
    fileid_end : int
        The ending ``fileid`` of interest.

    Returns
    -------
    bool
        True or False for whether or not the ``fileid`` is valid
    """

    # Make sure given fileids are integers
    try:
        int(fileid_start)
        int(fileid_end)
    except ValueError:
        return False

    # Make sure the given fileids are positive integers that is 15 digits or less
    if int(fileid_start) <= 0 or int(fileid_start) > 999999999999999:
        return False
    elif int(fileid_end) <= 0 or int(fileid_end) > 999999999999999:
        return False

    # Make sure the given fileids are increasing in value over the range
    if int(fileid_start) >= int(fileid_end):
        return False

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
