"""This module contains functions to perform various queries on the database.

Authors
-------

    - Matthew Bourque

Use
---

    The functions within are intended to be imported and used by other modules,
    e.g.:
    ::
        from lasp_sdtp.database.database_queries import query_for_files
        data = query_for_files(fileid)
"""

import logging

from lasp_sdtp.database.database_controller import db
from lasp_sdtp.config import subscriber_config

logger = logging.getLogger(__name__)


def query_for_accounts_by_mission(mission: str) -> list:
    """Return the accounts associated with the given ``mission``

    Parameters
    ----------
    mission : str
        The mission of interest (e.g. ``TSIS2``)

    Returns
    -------
    accounts : list
        The account(s) that are subscribed to the given ``mission``
    """

    logger.info('Querying for accounts for mission %s' % mission)

    results = db.session.query(db.MissionAccountMapping).filter(db.MissionAccountMapping.mission == mission).all()
    accounts = [item.account for item in results]

    return accounts


def query_for_account_by_username(username: str) -> dict:
    """Return account information for the given ``username``

    Parameters
    ----------
    username : str
        The username of interest

    Returns
    -------
    account : dict
        The account information
    """

    logger.info('Querying for accounts for user %s' % username)

    results = db.session.query(db.Accounts).filter(db.Accounts.username == username).all()
    if results:
        account = results[0].__dict__
    else:
        account = None

    return account


def query_for_filelist(tags: dict) -> list:
    """Return a list of files (and their metadata) based on user-provided
    tags.

    Parameters
    ----------
    tags : dict
        A dictionary of key/value pairs for the request tags

    Returns
    -------
    results : list
        A list of database entries returned by the query
    """

    logger.info('Querying for files with parameters %s' % str(tags))

    # Build the query
    query = db.session.query(db.Files)  # base query
    query = query.filter(db.Files.stream == tags['stream'])  # stream is always supplied via default value
    query = query.filter(db.Files.version == tags['version'])  # version is always supplied via default value

    # For non-default shortname values
    if tags['shortname'] != 'all':
        query = query.filter(db.Files.shortname == tags['shortname'])

    # Order the results by fileid
    query = query.order_by(db.Files.fileid)

    # Run the query
    results = query.all()

    # Parse the query results
    results = [item.__dict__ for item in results]
    for item in results:
        del item['_sa_instance_state']

    # Only return files that the user has access to
    # Get missions associated with account
    missions = db.session.query(
                   db.MissionAccountMapping
               ).filter(
                   db.MissionAccountMapping.account == subscriber_config['username']
               ).all()
    missions = [item.mission for item in missions]

    # Get shortnames associated with missions
    shortnames = db.session.query(
                     db.MissionShortnameMapping
                 ).filter(
                     db.MissionShortnameMapping.mission.in_(missions)
                 ).all()
    shortnames = [item.shortname for item in shortnames]

    # Filter out the shortnames
    results = [result for result in results if result['shortname'] in shortnames]

    return results


def query_for_file(fileid: int) -> object:
    """Return the metadata associated with the given ``fileid``

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest

    Returns
    -------
    file_metadata : object
        The file metadata associated with the given ``fileid``
    """

    logger.info('Querying for fileid %s' % str(fileid))

    files = db.session.query(db.Files).filter(db.Files.fileid == fileid).all()
    file_metadata = files[0]  # There should only be one entry

    return file_metadata


def query_for_mission_by_shortname(shortname: str) -> str:
    """Return the mission associated with the given ``shortname``

    Parameters
    ----------
    shortname : str
        The shortname of interest (e.g. ``TSIS2_L1``)

    Returns
    -------
    mission : str
        The mission associated with the shortname (e.g. ``TSIS2``)
    """

    logger.info('Querying for mission(s) associated with shortname %s' % shortname)

    results = db.session.query(
                  db.MissionShortnameMapping
              ).filter(
                  db.MissionShortnameMapping.shortname == shortname
              ).all()
    mission = results[0].mission

    return mission


def query_for_queue_entries(fileid: int) -> list:
    """Return a list of ``FileQueue`` database table entries that exist for the
    given ``fileid``

    Parameters
    ----------
    fileid : int
        The ``fileid`` of interest

    Returns
    -------
    queue_entries : list
        A list of database entries that exist in the queue for the given
        ``fileid``
    """

    logger.info('Querying file queue for fileid %s' % str(fileid))

    queue_entries = db.session.query(db.FileQueue).filter(db.FileQueue.fileid == fileid).all()
    queue_entries = [item.__dict__ for item in queue_entries]

    return queue_entries


def query_for_tags_and_extras(fileids: list) -> list:
    """Return a list of tag and extra values from the ``TagsAndExtras`` table
    for the given list of files.

    Parameters
    ----------
    fileids: list
        A list of files to gather tags/extras for.

    Returns
    -------
    tags_and_extras: list
        A list of tag/extra values for the given ``fileids``.
    """

    logger.info('Querying for tags and extras for fileids %s' % fileids)

    tags_and_extras = []

    for fileid in fileids:

        result = db.session.query(db.TagsAndExtras).filter(db.TagsAndExtras.fileid == fileid).all()
        result = [item.__dict__ for item in result]
        for item in result:
            del item['_sa_instance_state']
        tags_and_extras.append(result)

    return tags_and_extras
