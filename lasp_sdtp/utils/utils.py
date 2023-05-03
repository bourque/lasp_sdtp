"""Various utility functions to help support the ``lasp_sdtp`` application.

Authors
-------
    Matthew Bourque

Example
-------

    ::
        from lasp_sdtp.utils.utils import get_checksum

TODO: Do something better with get_tag_value
"""

import hashlib
import json
import logging
import re

from flask import abort
from flask.wrappers import Response

from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database.controller import db
from lasp_sdtp.database.queries import query_for_file

logger = logging.getLogger(__name__)


def _get_subscriber_tags_and_extras(stream: str):
    """Returns a list of the subscriber-provided tags and extras for the given
    stream.

    Parameters
    ----------
    stream : str
        The stream of interest (e.g. ``prod``)

    Returns
    -------
    subscriber_tags : list of tuples
        The subscriber tags and associated metadata in the form of a tuple
        (i.e. ``(tag_name, default_value, data_type)``)
    subscriber_extras : list of tuples
        The subscriber extras and associated metadata in the form of a tuple
        (i.e. ``(extras_name, default_value, data_type)``)
    """

    # Store the tags and extras in a list
    # Values are stored as tuples, e.g. ('tag_name', 'default_value', 'type')
    subscriber_tags, subscriber_extras = [], []

    # Make sure the stream is in the subscriber configuration
    # If it isn't, then no data will be returned
    if stream in subscriber_config['streams']:

        # Get the tags
        for tag in subscriber_config['streams'][stream]['tags']:
            subscriber_tags.append((
                tag,
                subscriber_config['streams'][stream]['tags'][tag]['default'],
                eval(subscriber_config['streams'][stream]['tags'][tag]['type'])
            ))

        # Get the extras
        for extra in subscriber_config['streams'][stream]['extras']:
            subscriber_extras.append((
                extra,
                subscriber_config['streams'][stream]['extras'][extra]['default'],
                eval(subscriber_config['streams'][stream]['extras'][extra]['type'])
            ))

    return subscriber_tags, subscriber_extras


def combine_metadata(filelist: list, tags_and_extras: list) -> list:
    """Create a dictionary containing file metadata, tags, and extras, to comply
    with the ICD, e.g.:

    {
        'fileid': 4542,
        'expires': datetime.datetime(2023, 3, 8, 0, 0),
        'size': 47.0,
        'name': 'tsis2_tim_L2_v01_20220105.zip',
        'checksum': 'sha256:dtjeijvhnlexw28irt24j9kc18wgn1rwdlmm2sf505wczoopnld7zllhw1loqs3t',
        'tags': {'shortname': 'TSIS2_TIM_L2', 'stream': 'prod', 'version': 'v01'},
        'extras': {'irradiance', '1234.5'}
    }

    Parameters
    ----------
    filelist : list
        A list of dictionaries containing file metadata.
    tags_and_extras : list
        A list of dictionaries containing tag and/or extra values.

    Returns
    -------
    restructured_results : list
        A list of dictionaries containing file metadata, tags, and extras.
    """

    default_tag_keys = ['stream', 'shortname', 'version']
    restructured_results = []

    for file_data, tag_and_extra_data in zip(filelist, tags_and_extras):

        # Initialize dictionaries to store the separated data
        file_dict, tag_dict, extra_dict = {}, {}, {}

        # Filter out the default tags from the nominal file data
        for key in file_data:
            if key in default_tag_keys:  # Put the default tag keys into the tag_dict
                tag_dict[key] = file_data[key]
            else:  # Otherwise, it just goes in the file_dict
                file_dict[key] = file_data[key]

        # Put the subscriber supplied tags and extras into the tag/extra dict
        if tag_and_extra_data:
            for item in tag_and_extra_data:
                if item['field_type'] == 'tag':
                    tag_dict[item['field_name']] = item['value']
                elif item['field_type'] == 'extra':
                    extra_dict[item['field_name']] = item['value']

        # Bring all of these data together into one dictionary
        file_dict['tags'] = tag_dict
        if extra_dict:
            file_dict['extras'] = extra_dict

        restructured_results.append(file_dict)

    return restructured_results


def filter_for_subscriber_tags(data, tags, request):
    """Filters the given filelist for subscriber tag values

    Parameters
    ----------
    data : list
        A list of dictionaries containing file metadata, tags, and extras.
    tags : list
        A dictionary of key/value pairs for the request tags
    request : obj
        The request containing the subscriber tag arguments (e.g.
        ``GET /files?subscriber_tag=some_value``)

    Returns
    -------
    data : list
        The list of files that that match the given subscriber tag criteria
    """

    subscriber_tags, _ = _get_subscriber_tags_and_extras(tags['stream'])
    subscriber_tags = [tag[0] for tag in subscriber_tags]  # Only care about the tag name here
    filter_criteria = []
    for arg in request.args.keys():
        if arg in subscriber_tags:
            filter_criteria.append((arg, request.args[arg]))
    for item in filter_criteria:
        filter_name, filter_value = item
        data = [item for item in data if filter_name in item['tags'] and item['tags'][filter_name] == filter_value]

    return data


def get_checksum(file) -> str:
    """Return a randomly generated checksum.  Currently, only supports the
    ``sha256`` checksum type.

    Parameters
    ----------
    filename : str
        The path to the file to generate the checksum for

    Returns
    -------
    checksum : str
        A randomly generated checksum based on the ``checksum_type`` given in
        the system configuration
    """

    # Check that the checksum type is supported
    supported_checksum_types = ['sha256']
    checksum_type = subscriber_config['checksum_type']
    if checksum_type not in supported_checksum_types:
        raise NotImplementedError(f'Checksum type {checksum_type} is currently not supported')

    # Create checksum
    with open(file, 'rb') as f:
        bytes = f.read()
        checksum = f'sha256:{hashlib.sha256(bytes).hexdigest()}'

    return checksum


def get_shortname(filename: str) -> str:
    """Return the appropriate value for the ``shortname`` tag for the given
    filename.  Currently, this is hard-coded to only support TSIS-2.

    Parameters
    ----------
    filename : str
        The filename of interest (e.g. ``tsis2_tim_L2_v01_20220422.zip``)

    Returns
    -------
    matched_shortname : str or None
        The ``shortname`` that matches the given filename (e.g.
        ``TSIS2_TIM_L2``)
    """

    shortnames = db.session.query(db.Shortnames).all()

    matched_shortname = None
    for shortname in shortnames:
        match = re.match(shortname.filename_pattern, filename)
        if match:
            matched_shortname = shortname.shortname
            break

    return matched_shortname


def get_tag_value(filename: str, field_name: str) -> object:
    """Retrieve and return the tag value for the given file and ``field_name``

    Parameters
    ----------
    filename : str
        The file from which to retrieve the tag value
    field_name : str
        The name of the tag to retrieve

    Returns
    -------
    value : obj
        The tag value
    """

    #logger.info('Retrieving %s from %s', (field_name, filename))
    return 'some_value'


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
        logger.critical('Problem with response from %s API', api)
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

    # Convert the request arguments to mutable dict and make all keys lowercase,
    # to avoid case sensitivity issues
    request_args = request.args.to_dict()
    request_args = {key.lower(): value for key, value in request_args.items()}

    # Define the default supported tags
    default_tag_list = [
        ('stream', 'prod', str),
        ('shortname', 'all', str),
        ('version', '01', str),
        ('maxfile', subscriber_config['max_num_files'], int),
        ('startfileid', 1, int)]

    # Determine the stream of the request
    if 'stream' in request_args.keys():
        stream = request_args['stream']
    else:
        stream = 'prod'  # If no stream is given, assume prod

    # Get the subscriber tags and extras for the stream
    subscriber_tags, subscriber_extras = _get_subscriber_tags_and_extras(stream)

    # Supported tags is an aggregation of the default + subscriber-defined tags
    supported_tags_and_extras = default_tag_list + subscriber_tags + subscriber_extras

    # Check to see if any of the provided tags in the request are not supported
    for item in request_args.keys():
        if item not in [item[0] for item in supported_tags_and_extras]:
            abort(400)

    # Store tags from request in a dictionary
    tags = {}
    for tag_name, default_value, data_type in supported_tags_and_extras:
        if tag_name in request_args:
            tags[tag_name] = data_type(request_args[tag_name])
        else:
            tags[tag_name] = data_type(default_value)

    return tags


def validate_access(fileid: str) -> bool:
    """Check that the subscriber has access to the provided file (indicated by
    the ``fileid``).

    Parameters
    ----------
    fileid : str
        The ``fileid`` given in the request

    Returns
    -------
    bool
        True or False for whether or not the subscriber has access to the file
    """

    # Get the shortname for the file
    file_metadata = query_for_file(fileid)
    shortname = file_metadata.shortname

    # Check to see the subscriber has access to the shortname
    # Get missions associated with account
    missions = db.session.query(
                   db.MissionAccountMapping
               ).filter(
                   db.MissionAccountMapping.account == subscriber_config['username']
               ).all()
    missions = [item.mission for item in missions]

    # Get shortnames associated with missions
    allowed_shortnames = db.session.query(
                             db.MissionShortnameMapping
                         ).filter(
                             db.MissionShortnameMapping.mission.in_(missions)
                         ).all()
    allowed_shortnames = [item.shortname for item in allowed_shortnames]

    if shortname in allowed_shortnames:
        return True
    else:
        return False


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

    # Make sure the maxfile tag does not exceed the max number of files agreement
    if tags['maxfile'] > subscriber_config['max_num_files']:
        return False

    # Make sure the startfileid is a valid fileid
    if not validate_fileid(tags['startfileid']):
        return False

    # If all the checks passed, the tags are valid
    return True
