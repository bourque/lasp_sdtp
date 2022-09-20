"""This module houses functions to perform various queries on the database.

Authors
-------

    - Matthew Bourque

Use
---

    The functions within are intended to be imported and used by other modules,
    e.g.:
    ::
        from lasp_sdtp.database.database_queries import query_for_available_files
        data = query_for_available_files(fileid)
"""

import datetime
import logging

from lasp_sdtp.database.database_controller import db
from lasp_sdtp.config import subscriber_config

logger = logging.getLogger(__name__)


def query_for_account(username: str) -> dict:
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

    logger.info('Querying accounts database table for %s account' % username)

    results = db.session.query(db.Accounts).filter(db.Accounts.username == username).all()
    if results:
        account = results[0].__dict__
    else:
        account = None

    return account


def query_for_available_files(fileid: int) -> object:
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

    logger.info('Querying available_files database table for file %s' % str(fileid))

    available_files = db.session.query(db.AvailableFiles).filter(db.AvailableFiles.fileid == fileid).all()
    file_metadata = available_files[0]  # There should only be one entry

    return file_metadata


def query_for_filelist(tags: dict) -> list:
    """Return a list of files (and their metadata) based on user-provided
    tags.

    For the ``date`` tag, the user may provide a specific date to filter on
    (e.g. ``date=2022-01-01``) or the user may provide a specific date range
    to filter on via the ``start_date`` and ``end_date`` tags (e.g.
    ``start_date=2022-01-01&end_date=2022-02-01``).  If a ``date`` is
    provided, then ``start_date`` and ``end_date`` must remain as ``None``.
    Alternatively, if both a ``start_date`` and ``end_date`` are provided,
    the ``date`` tag must remain as ``None``.

    Parameters
    ----------
    tags : dict
        A dictionary of key/value pairs for the request tags

    Returns
    -------
    results : list
        A list of database entries returned by the query
    """

    logger.info('Querying available_files database table for files with parameters %s' % str(tags))

    # Build the query
    query = db.session.query(db.AvailableFiles)  # base query
    query = query.filter(db.AvailableFiles.stream == tags['stream'])  # stream is always supplied via default value
    query = query.filter(db.AvailableFiles.version == tags['version'])  # version is always supplied via default value

    # For non-default shortname values
    if tags['shortname'] != 'all':
        query = query.filter(db.AvailableFiles.shortname == tags['shortname'])

    # For non-default date values
    if tags['date'] is not None:
        query = query.filter(db.AvailableFiles.date == datetime.datetime.strptime(tags['date'], '%Y-%m-%d').date())

    # For non-default start_date and end_date values
    if tags['start_date'] and tags['end_date'] is not None:
        query = query.filter(db.AvailableFiles.date >= datetime.datetime.strptime(tags['start_date'], '%Y-%m-%d').date())
        query = query.filter(db.AvailableFiles.date <= datetime.datetime.strptime(tags['end_date'], '%Y-%m-%d').date())

    # Order the results by fileid
    query = query.order_by(db.AvailableFiles.fileid)

    # Run the query
    results = query.all()

    # Parse the query results
    results = [item.__dict__ for item in results]
    for item in results:
        del item['_sa_instance_state']

    # Only return files that the user has access to
    allowed_data_products = query_for_account(subscriber_config['username'])['allowed_data_products']
    allowed_data_products = allowed_data_products.split(',')
    allowed_data_products = [item.strip() for item in allowed_data_products]
    results = [result for result in results if result['data_product_id'] in allowed_data_products]

    return results


def query_for_metadata(fileids: list) -> list:
    """Return a list of tag and extra values from the ``metadata`` table for
    the given list of files.

    Parameters
    ----------
    fileids: list
        A list of files to gather tags/extras for.

    Returns
    -------
    tags_and_extras: list
        A list of tag/extra values for the given ``fileids``.
    """

    tags_and_extras = []

    for fileid in fileids:

        result = db.session.query(db.Metadata).filter(db.Metadata.fileid == fileid).all()
        result = [item.__dict__ for item in result]
        for item in result:
            del item['_sa_instance_state']
        tags_and_extras.append(result)

    return tags_and_extras


def query_for_queue_entries(fileid: int) -> list:
    """Return a list of queue database table entries that exist for the
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

    logger.info('Querying file_queue database table for file %s' % str(fileid))

    queue_entries = db.session.query(db.FileQueue).filter(db.FileQueue.fileid == fileid).all()
    queue_entries = [item.__dict__ for item in queue_entries]

    return queue_entries
