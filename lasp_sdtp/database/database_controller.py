"""This module is used to connect to and interact with the LASP SDTP
application database.

The ``connect()`` method within this module allows the user to connect to the
``lasp_sdtp_db`` database via the ``session``, ``base``, and ``engine`` objects
(described below).  The classes within serve as ORMs that define the individual
tables of the relational database.

The ``engine`` object serves as the low-level database API and perhaps most
importantly contains dialects which allows the ``sqlalchemy`` module to
communicate with the database.

The ``base`` object serves as a base class for class definitions.  It produces
``Table`` objects and constructs ORMs.

The ``session`` object manages operations on ORM-mapped objects, as construced
by the base. These operations include querying, for example.

Authors
-------
    - Matthew Bourque

Use
---

tbd

"""

import datetime
import logging
import os
from typing import Optional

from sqlalchemy import Table
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.sql.schema import MetaData

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config
from lasp_sdtp.database import database_interface


class DatabaseController():
    """
    """

    def __init__(self):
        """
        """

        self.session, self.base, self.engine, self.meta = self.connect()
        self.Accounts = database_interface.Accounts
        self.FileMetadata = database_interface.FileMetadata
        self.FileQueue = database_interface.FileQueue
        self.Transactions = database_interface.Transactions

    def connect(self) -> (Session, DeclarativeMeta, Engine, MetaData):
        """Return ``session``, ``base``, ``engine``, and ``metadata`` objects for
        connecting to the ``last_sdtp_db`` database.

        Create an ``engine`` using an given ``connection_string``. Create a ``base``
        class and ``session`` class from the ``engine``. Create an instance of the
        ``session`` class. Return the ``session``, ``base``, and ``engine``
        instances.

        Returns
        -------
        session : sesson object
            Provides a holding zone for all objects loaded or associated with the
            database.
        base : base object
            Provides a base class for declarative class definitions.
        engine : engine object
            Provides a source of database connectivity and behavior.
        meta: metadata object
            The connection metadata
        """

        connection_string = admin_config['db_connection_string']
        engine = create_engine(connection_string, echo=False)
        base = declarative_base(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        meta = MetaData(engine)

        logging.info(f'Connected to database {admin_config["db_connection_string"]}')

        return session, base, engine, meta

    def insert_data(self, table_name: str, data: list[dict]):
        """Inserts the given data into the given table

        Parameters
        ----------
        table : str
            The table to insert data into (e.g. ``accounts``)
        data : list of dicts
            The data to insert
        """

        table = Table(table_name, self.base.metadata, autoload=True)
        for row in data:
            db.engine.execute(table.insert().values(row))

    def mark_transaction_complete(self, fileid: int):
        """Update the ``transactions`` table to mark the the GET request
        transaction corresponding to the given ``fileid`` as complete by adding the
        ``end_time``

        Parameters
        ----------
        transactionid : int
            The ``transactionid`` of interest
        """

        end_time = datetime.datetime.now()
        self.session.query(self.Transactions).\
            filter(self.Transactions.fileid == fileid).\
            filter(self.Transactions.username == subscriber_config['username']).\
            update({'end_time': end_time})
        self.session.commit()
        logging.info(f'Transaction for {fileid} for {subscriber_config["username"]} account marked complete')

    def update_transactions_table(self, request: object, fileid: Optional[int] = None) -> int:
        """Insert information for a new transaction in the ``transactions`` table

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
                start_time=datetime.datetime.now())

        # For GET /files
        elif request.method == 'GET' and fileid is None:
            data_to_insert = self.Transactions(
                action=f'{request.method} {request.url}',
                username=subscriber_config['username'],
                start_time=datetime.datetime.now())

        # For GET /files/<fileid>
        elif request.method == 'GET' and fileid is not None:
            data_to_insert = self.Transactions(
                action=f'{request.method} {request.url}',
                username=subscriber_config['username'],
                start_time=datetime.datetime.now(),
                fileid=fileid,
                source=admin_config['filesystem_loc'],
                destination=admin_config['data_cache_loc'])

        # For DELETE /files/<fileid>
        if request.method == 'DELETE':
            url = os.path.join(os.path.dirname(request.url), str(fileid))
            data_to_insert = self.Transactions(
                action=f'{request.method} {url}',
                username=subscriber_config['username'],
                start_time=datetime.datetime.now())

        # Insert the data, and get the transaction id
        self.session.add(data_to_insert)
        self.session.flush()
        transactionid = data_to_insert.transactionid
        self.session.commit()

        logging.info(f'Recorded transaction {transactionid} for request {request}')

        return transactionid


db = DatabaseController()
