"""This module is used to interact with the database for the LASP SDTP
interface.

The ``load_connection()`` function within this module allows the user to
connect to the ``lasp_sdtp_db`` database via the ``session``, ``base``, and
``engine`` objects (described below).  The classes within serve as ORMs that
define the individual tables of the relational database.

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

    Users can interact with the existing database tables by importing various
    connection objects and database tables, for example:

    ::

        from lasp_sdtp.database.database import SomeTable
        from lasp_sdtp.database.database import session

        results = session.query(SomeTable).all()
"""

import datetime
import logging
import os

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from lasp_sdtp.config import admin_config
from lasp_sdtp.config import subscriber_config


def load_connection():
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


# Create a global session so that it can easily be imported
session, base, engine, meta = load_connection()


def _mark_transaction_complete(transactionid):
    """Update the ``transactions`` table to mark the given ``transactionid`` as
    complete by adding the ``end_time``

    Parameters
    ----------
    transactionid : int
        The ``transactionid`` of interest
    """

    end_time = datetime.datetime.now()
    session.query(Transactions).filter(Transactions.transactionid == transactionid).update({'end_time': end_time})
    session.commit()
    logging.info(f'Transaction {transactionid} marked complete')


def _update_transactions_table(request, fileid=None):
    """Insert information for a new transaction in the ``transactions`` table

    Parameters
    ----------
    request : ``request`` obj
        The request made by the server.  Must have ``method`` and a ``url``
        attributes
    fileid : int or None
        The ``fileid`` that is part of the request, if applicable

    Returns
    -------
    transactionid : int
        The ``transactionid`` that was used in the database table entry
    """

    # For PUT /register
    if request.method == 'PUT':
        data_to_insert = Transactions(
            action=f'{request.method} {request.url}',
            username=subscriber_config['username'],
            start_time=datetime.datetime.now())

    # For GET /files
    elif request.method == 'GET' and fileid is None:
        data_to_insert = Transactions(
            action=f'{request.method} {request.url}',
            username=subscriber_config['username'],
            start_time=datetime.datetime.now())

    # For GET /files/<fileid>
    elif request.method == 'GET' and fileid is not None:
        data_to_insert = Transactions(
            action=f'{request.method} {request.url}',
            username=subscriber_config['username'],
            start_time=datetime.datetime.now(),
            fileid=fileid,
            source=admin_config['filesystem_loc'],
            destination=admin_config['data_cache_loc'])

    # For DELETE /files/<fileid>
    if request.method == 'DELETE':
        url = os.path.join(os.path.dirname(request.url), str(fileid))
        data_to_insert = Transactions(
            action=f'{request.method} {url}',
            username=subscriber_config['username'],
            start_time=datetime.datetime.now())

    # Insert the data, and get the transaction id
    session.add(data_to_insert)
    session.flush()
    transactionid = data_to_insert.transactionid
    session.commit()

    logging.info(f'Recorded transaction {transactionid} for request {request}')

    return transactionid


def insert_data(table_name, data):
    """Inserts the given data into the given table

    Parameters
    ----------
    table_name : str
        The name of the table (e.g. ``accounts``)
    data : list of dicts
        The data to insert
    """

    table = Table(table_name, base.metadata)
    table.insert().execute(data)


class Accounts(base):
    """ORM for the ``accounts`` table"""

    __tablename__ = 'accounts'
    __table_args__ = (UniqueConstraint('userid', 'username', 'certuid', name='accounts_uc'),)

    # Define the columns
    userid = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    certuid = Column(String(20), unique=True, nullable=False)
    role = Column(Enum('admin', 'subscriber', name='role'), nullable=False)
    registration_date = Column(DateTime, nullable=False)
    registration_expires = Column(DateTime)


class FileMetadata(base):
    """ORM for the ``file_metadata`` table"""

    __tablename__ = 'file_metadata'
    __table_args__ = (UniqueConstraint('fileid', 'name', 'checksum', name='file_metadata_uc'),)

    # Define the columns
    fileid = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    checksum = Column(String(71), unique=True, nullable=False)
    size = Column(Float, nullable=False)
    expires = Column(DateTime, nullable=False)
    stream = Column(String(255), nullable=False)
    shortname = Column(String(255), nullable=False)
    version = Column(String(3), nullable=False)
    date = Column(DateTime, nullable=False)


class FileQueue(base):
    """ORM for the ``file_queue`` table"""

    __tablename__ = 'file_queue'
    __table_args__ = (UniqueConstraint('queueid', 'username', 'fileid', name='file_queue_uc'),)

    # Define the columns
    queueid = Column(Integer, primary_key=True)
    username = Column(String(30), nullable=False)
    fileid = Column(Integer, nullable=False)
    entry_date = Column(DateTime, nullable=False)
    expires = Column(DateTime, nullable=False)


class Transactions(base):
    """ORM for the ``transactions`` table"""

    __tablename__ = 'transactions'

    # Define the columns
    transactionid = Column(Integer, primary_key=True)
    action = Column(String(255), nullable=False)
    username = Column(String(30), nullable=False)
    start_time = Column(DateTime, nullable=False)
    fileid = Column(Integer)
    source = Column(String(255))
    destination = Column(String(255))
    end_time = Column(DateTime)
