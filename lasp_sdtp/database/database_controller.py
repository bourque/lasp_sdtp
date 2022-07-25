"""This module is used to connect to and interact with the ``lasp_sdtp``
database.

The ``connect()`` method within this module allows the user to connect to the
``lasp_sdtp_db`` database via the ``session``, ``base``, and ``engine`` objects
(described below).  The classes within serve as ORMs that define the individual
tables of the relational database.

The ``engine`` object serves as the low-level database API and perhaps most
importantly contains dialects which allows the ``sqlalchemy`` module to
communicate with the database.

The ``base`` object serves as a base class for class definitions.  It produces
``Table`` objects and constructs ORMs.

The ``session`` object manages operations on ORM-mapped objects, as constructed
by the base. These operations include querying, for example.

Authors
-------

    - Matthew Bourque

Use
---

    To interact with the database, import the instantiated
    ``DatabaseController`` class:
    ::
        from lasp_sdtp.database.database_controller import db
"""

import datetime
import logging
from pathlib import Path
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.sql.schema import MetaData

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database import database_interface

logger = logging.getLogger(__name__)


class DatabaseController():
    """A class for interacting with the ``lasp_sdtp`` database.

    Attributes
    ----------

    Methods
    -------

    """

    def __init__(self):

        self.session, self.base, self.engine, self.meta = self.connect()
        self.Accounts = database_interface.Accounts
        self.FileMetadata = database_interface.FileMetadata
        self.FileQueue = database_interface.FileQueue
        self.Transactions = database_interface.Transactions

    def connect(self) -> (Session, DeclarativeMeta, Engine, MetaData):
        """Return ``session``, ``base``, ``engine``, and ``metadata`` objects
        for connecting to the ``last_sdtp`` database.

        Create an ``engine`` using a given ``connection_string``. Create a
        ``base`` class and ``session`` class from the ``engine``. Create an
        instance of the ``session`` class. Return the ``session``, ``base``, and
        ``engine`` instances.

        Returns
        -------
        session : session object
            Provides a holding zone for all objects loaded or associated with
            the database.
        base : base object
            Provides a base class for declarative class definitions.
        engine : engine object
            Provides a source of database connectivity and behavior.
        meta: metadata object
            The connection metadata
        """

        connection_string = admin_config['db_connection_string']
        engine = sa.create_engine(connection_string, echo=False)
        base = declarative_base(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        meta = MetaData(engine)

        logger.info('Connected to database %s' % admin_config["db_connection_string"])

        return session, base, engine, meta

    def delete_file_from_queue(self, fileid: int):
        """Remove the ``file_queue`` database entry for the given ``fileid``

        Parameters
        ----------
        fileid : int
            The ``fileid`` of interest
        """

        self.session.query(self.FileQueue).filter(self.FileQueue.fileid == fileid).delete()
        self.session.commit()
        logger.info('Deleted %s from file queue' % fileid)

    def insert_data(self, table_name: str, data: list[dict]):
        """Inserts the given data into the given table

        Parameters
        ----------
        table : str
            The table to insert data into (e.g. ``accounts``)
        data : list of dicts
            The data to insert
        """

        table = sa.Table(table_name, self.base.metadata, autoload=True)
        for row in data:
            self.engine.execute(table.insert().values(row))
            logger.info('Inserted the following into the database: %s' % row)

    def mark_transaction_complete(self, fileid: int):
        """Update the ``transactions`` table to mark the GET request transaction
        corresponding to the given ``fileid`` as complete by adding the
        ``end_time``

        Parameters
        ----------
        transactionid : int
            The ``transactionid`` of interest
        """

        end_time = datetime.datetime.utcnow()
        self.session.query(
            self.Transactions
        ).filter(
            self.Transactions.fileid == fileid,
            self.Transactions.username == subscriber_config['username']
        ).update(
            {'end_time': end_time})
        self.session.commit()
        logger.info('Transaction for %s for %s account marked complete' % (fileid, subscriber_config['username']))

    def query_for_account(self, username: str) -> list:
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

        results = self.session.query(self.Accounts).filter(self.Accounts.username == username).all()
        if results:
            account = results[0].__dict__
        else:
            account = None

        return account

    def query_for_filelist(self, tags: dict) -> list:
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

        logger.info('Querying file_metadata database table for files with parameters %s' % str(tags))

        query = self.session.query(self.FileMetadata)  # base query
        query = query.filter(self.FileMetadata.stream == tags['stream'])  # stream is always supplied via default value
        query = query.filter(self.FileMetadata.version == tags['version'])  # version is always supplied via default value

        # For non-default shortname values
        if tags['shortname'] != 'all':
            query = query.filter(self.FileMetadata.shortname == tags['shortname'])

        # For non-default date values
        if tags['date'] is not None:
            query = query.filter(self.FileMetadata.date == datetime.datetime.strptime(tags['date'], '%Y-%m-%d').date())

        # For non-default start_date and end_date values
        if tags['start_date'] and tags['end_date'] is not None:
            query = query.filter(self.FileMetadata.date >= datetime.datetime.strptime(tags['start_date'], '%Y-%m-%d').date())
            query = query.filter(self.FileMetadata.date <= datetime.datetime.strptime(tags['end_date'], '%Y-%m-%d').date())

        results = query.all()

        # Parse the query results
        results = [item.__dict__ for item in results]
        for item in results:
            del item['_sa_instance_state']

        return results

    def query_for_filename(self, fileid: int) -> str:
        """Return the filename associated with the given ``fileid``

        Parameters
        ----------
        fileid : int
            The ``fileid`` of interest

        Returns
        -------
        filename : str
            The name of the file for the given ``fileid``
        """

        logger.info('Querying file_metadata database table for file %s' % str(fileid))

        file_metadata = self.session.query(self.FileMetadata.name).filter(self.FileMetadata.fileid == fileid).all()
        filename = file_metadata[0][0]

        return filename

    def query_for_queue_entries(self, fileid: int) -> list:
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

        queue_entries = self.session.query(self.FileQueue).filter(self.FileQueue.fileid == fileid).all()
        queue_entries = [item.__dict__ for item in queue_entries]

        return queue_entries

    def update_transactions_table(self, request: object, fileid: Optional[int] = None) -> int:
        """Insert information for a new transaction in the ``transactions``
        table

        Parameters
        ----------
        request : ``request`` obj
            The request made by the server.  Must have ``method`` and a ``url``
            attributes
        fileid : int, optional
            The ``fileid`` that is part of the request, if applicable

        Returns
        -------
        transactionid : int
            The ``transactionid`` that was used in the database table entry
        """

        # For PUT /register
        if request.method == 'PUT':
            data_to_insert = self.Transactions(
                action=f'{request.method} {request.url}',
                username=subscriber_config['username'],
                start_time=datetime.datetime.utcnow())

        # For GET /files
        elif request.method == 'GET' and fileid is None:
            data_to_insert = self.Transactions(
                action=f'{request.method} {request.url}',
                username=subscriber_config['username'],
                start_time=datetime.datetime.utcnow())

        # For GET /files/<fileid>
        elif request.method == 'GET' and fileid is not None:
            data_to_insert = self.Transactions(
                action=f'{request.method} {request.url}',
                username=subscriber_config['username'],
                start_time=datetime.datetime.utcnow(),
                fileid=fileid,
                source=admin_config['filesystem_loc'],
                destination=admin_config['data_cache_loc'])

        # For DELETE /files/<fileid>
        elif request.method == 'DELETE':
            url = Path(request.url).parent / str(fileid)
            data_to_insert = self.Transactions(
                action=f'{request.method} {url}',
                username=subscriber_config['username'],
                start_time=datetime.datetime.utcnow())

        else:
            raise ValueError(f'Request method {request.method} is not recorgnized')

        # Insert the data, and get the transaction id
        self.session.add(data_to_insert)
        self.session.flush()
        transactionid = data_to_insert.transactionid
        self.session.commit()

        logger.info('Recorded transaction %s for request %s' % (str(transactionid), request))

        return transactionid


db = DatabaseController()
