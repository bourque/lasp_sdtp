"""This module is used to connect to and interact with the database.

The ``connect()`` method within this module allows the user to connect to the
database via the ``session``, ``base``, and ``engine`` objects (described
below).

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
    ``DatabaseController`` class, e.g.:
    ::
        from lasp_sdtp.database.database_controller import db
        db.delete_file_from_queue(1)
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
    """A class for interacting with the database.

    Attributes
    ----------
    Accounts : ``sqlalchemy.orm.decl_api.DeclarativeMeta`` object
        The ORM for the ``Accounts`` database table
    base : ``sqlalchemy.orm.decl_api.DeclarativeMeta`` object
        Provides a base class for declarative class definitions.
    engine : ``sqlalchemy.engine.base.Engine`` object
        Provides a source of database connectivity and behavior.
    FileQueue : ``sqlalchemy.orm.decl_api.DeclarativeMeta`` object
        The ORM for the ``FileQueue`` database table
    Files : ``sqlalchemy.orm.decl_api.DeclarativeMeta`` object
        The ORM for the ``Files`` database table
    meta : ``sqlalchemy.sql.schema.MetaData`` object
        The connection metadata
    MissionAccountMapping : ``sqlalchemy.orm.decl_api.DeclarativeMeta`` object
        The ORM for the ``MissionAccountMapping`` database table
    Missions : ``sqlalchemy.orm.decl_api.DeclarativeMeta`` object
        The ORM for the ``Missions`` database table
    MissionShortnameMapping : ``sqlalchemy.orm.decl_api.DeclarativeMeta`` object
        The ORM for the ``MissionShortnameMapping`` database table
    session : ``sqlalchemy.orm.session.Session`` object
        Provides a holding zone for all objects loaded or associated with
        the database.
    Shortnames : ``sqlalchemy.orm.decl_api.DeclarativeMeta`` object
        The ORM for the ``Shortnames`` database table
    TagsAndExtras : ``sqlalchemy.orm.decl_api.DeclarativeMeta`` object
        The ORM for the ``TagsAndExtras`` database table
    Transactions : ``sqlalchemy.orm.decl_api.DeclarativeMeta`` object
        The ORM for the ``Transactions`` database table

    Methods
    -------
    connect()
        Return ``session``, ``base``, ``engine``, and ``metadata`` objects
        for connecting to the database.
    delete_file_from_queue(fileid)
        Remove the ``FileQueue`` database entry for the given ``fileid``
    insert_data(table_name, data)
        Inserts the given data into the given table
    mark_transaction_complete(fileid)
        Update the `Transactions`` table to mark the GET request transaction
        corresponding to the given ``fileid`` as complete by adding the
        ``end_time``
    update_mission_account_mapping()
        Update the ``MissionAccountMapping`` table with missions that the
        subscriber is subscribed to
    update_registration()
        Update the ``Accounts`` table with registration information
    update_transactions_table(request, fileid=None)
        Insert information for a new transaction in the ``Transactions``
        table
    """

    def __init__(self):

        self.session, self.base, self.engine, self.meta = self._connect()
        self.Accounts = database_interface.Accounts
        self.FileQueue = database_interface.FileQueue
        self.Files = database_interface.Files
        self.MissionAccountMapping = database_interface.MissionAccountMapping
        self.Missions = database_interface.Missions
        self.MissionShortnameMapping = database_interface.MissionShortnameMapping
        self.Shortnames = database_interface.Shortnames
        self.TagsAndExtras = database_interface.TagsAndExtras
        self.Transactions = database_interface.Transactions

    def _connect(self) -> (Session, DeclarativeMeta, Engine, MetaData):
        """Return ``session``, ``base``, ``engine``, and ``metadata`` objects
        for connecting to the ``last_sdtp`` database.

        Create an ``engine`` using a given ``connection_string``. Create a
        ``base`` class and ``session`` class from the ``engine``. Create an
        instance of the ``session`` class. Return the ``session``, ``base``, and
        ``engine`` instances.

        Returns
        -------
        session : ``sqlalchemy.orm.session.Session`` object
            Provides a holding zone for all objects loaded or associated with
            the database.
        base : ``sqlalchemy.orm.decl_api.DeclarativeMeta`` object
            Provides a base class for declarative class definitions.
        engine : ``sqlalchemy.engine.base.Engine`` object
            Provides a source of database connectivity and behavior.
        meta: ``sqlalchemy.sql.schema.MetaData`` object
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
        """Remove the ``FileQueue`` database entry for the given ``fileid``

        Parameters
        ----------
        fileid : int
            The ``fileid`` of interest
        """

        self.session.query(self.FileQueue).filter(self.FileQueue.fileid == fileid).delete()
        self.session.commit()
        logger.info('Deleted %s from file queue' % fileid)

    def insert_data(self, data: list[object]):
        """Inserts the given data into the appropriate table

        Parameters
        ----------
        data : list of ``sqlalchemy`` Table objects
            The data to insert
        """

        db.session.add_all(data)
        db.session.commit()

        for row in data:
            logger.info('Inserted the following into the database: %s' % row.__dict__)

    def mark_transaction_complete(self, fileid: int):
        """Update the ``Transactions`` table to mark the GET request transaction
        corresponding to the given ``fileid`` as complete by adding the
        ``end_time``

        Parameters
        ----------
        fileid : int
            The ``fileid`` of interest
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

    def update_mission_account_mapping(self):
        """Update the ``MissionAccountMapping`` table with missions that the
        subscriber is subscribed to"""

        missions = subscriber_config['missions']
        data_to_insert = []
        for mission in missions:
            data_to_insert.append(self.MissionAccountMapping(
                mission=mission,
                account=subscriber_config['username']
            ))
        self.insert_data(data_to_insert)
        logger.info('Mapped the following missions to account %s' % data_to_insert)

    def update_registration(self):
        """Update the ``Accounts`` table with registration information"""

        # Define metadata for the entry
        certuid = f'{subscriber_config["username"]}_cert'
        registration_date = datetime.datetime.utcnow().date()
        registration_expires = registration_date + datetime.timedelta(days=subscriber_config['account_expiration_period'])

        # Update ``accounts`` table
        self.session.query(
            db.Accounts
        ).filter(
            db.Accounts.username == subscriber_config['username']
        ).update(
            {'registration_open': False,
             'certuid': certuid,
             'registration_date': registration_date,
             'registration_expires': registration_expires})

        db.session.commit()
        logger.info('Registered account for %s' % subscriber_config['username'])

    def update_transactions_table(self, request: object, fileid: Optional[int] = None) -> int:
        """Insert information for a new transaction in the ``Transactions``
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
            raise ValueError(f'Request method {request.method} is not recognized')

        # Insert the data, and get the transaction id
        self.session.add(data_to_insert)
        self.session.flush()
        transactionid = data_to_insert.transactionid
        self.session.commit()

        logger.info('Recorded transaction %s for request %s' % (str(transactionid), request))

        return transactionid


# Create an importable instance of the database session
db = DatabaseController()
