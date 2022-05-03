"""
A module to interact with the a testing database for the LASP SDTP implementation.

The ``load_connection()`` function within this module allows the user to connect
to the ``lasp_sdtp_db`` database via the ``session``, ``base``, and ``engine``
objects (described below).  The classes within serve as ORMs (Object-relational
mappings) that define the individual tables of the relational database.

The ``engine`` object serves as the low-level database API and perhaps most importantly
contains dialects which allows the ``sqlalchemy`` module to communicate with the database.

The ``base`` object serves as a base class for class definitions.  It produces ``Table``
objects and constructs ORMs.

The ``session`` object manages operations on ORM-mapped objects, as construced by the base.
These operations include querying, for example.

Authors
-------
    - Matthew Bourque

Use
---

    Executing the module on the command line will build the database
    tables defined within:

    ::

        python database.py

    Users wishing to interact with the existing database may do so by
    importing various connection objects and database tables, for
    example:

    ::

        from lasp_sdtp.database.database import SomeTable
        from lasp_sdtp.database.database import session

        results = session.query(SomeTable).all()
"""

import datetime
import os

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from lasp_sdtp.config import config


HOME_DIR = os.path.expanduser('~')
FILESYSTEM_PATH = f'{HOME_DIR}/Desktop/test_filesystem/'
SUBSCRIBER_QUEUE = f'{HOME_DIR}/Desktop/test_queue/'


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

    connection_string = config['connection_string']
    engine = create_engine(connection_string, echo=False)
    base = declarative_base(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    meta = MetaData(engine)

    return session, base, engine, meta


# Define a global session so that it can easily be imported
session, base, engine, meta = load_connection()


def _mark_transaction_complete(transactionid):
    """
    """

    end_time = str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    session.query(Transactions).filter(Transactions.transactionid == transactionid).update({'end_time': end_time, 'complete': 1})
    session.commit()


def _update_transactions_table(request, **kwargs):
    """
    """

    # For PUT /register
    if request.method == 'PUT':
        data_to_insert = Transactions(
            action=f'{request.method} {request.url}',
            subscriber_name=config['subscriber_name'],
            start_time=str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # For GET /files
    elif request.method == 'GET' and 'fileid' not in kwargs:
        data_to_insert = Transactions(
            action=f'{request.method} {request.url}',
            subscriber_name=config['subscriber_name'],
            start_time=str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # For GET /files/<fileid>
    elif request.method == 'GET' and 'fileid' in kwargs:
        data_to_insert = Transactions(
            action=f'{request.method} {request.url}',
            subscriber_name=config['subscriber_name'],
            start_time=str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            fileid=kwargs['fileid'],
            source=FILESYSTEM_PATH,
            destination=SUBSCRIBER_QUEUE)

    # For DELETE /files/<fileid>
    if request.method == 'DELETE':
        url = os.path.join(os.path.dirname(request.url), str(kwargs['fileid']))
        data_to_insert = Transactions(
            action=f'{request.method} {url}',
            subscriber_name=config['subscriber_name'],
            start_time=str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # Insert the data, and get the transaction id
    session.add(data_to_insert)
    session.flush()
    transactionid = data_to_insert.transactionid
    session.commit()

    return transactionid


class FileMetadata(base):
    """ORM for the ``file_metadata`` table"""

    __tablename__ = 'file_metadata'

    # Define the columns
    fileid = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    checksum = Column(String(71), unique=True, nullable=False)
    size = Column(Float, nullable=False)
    expires = Column(String(10), nullable=False)
    stream = Column(String(255), nullable=False)
    shortname = Column(String(255), nullable=False)
    version = Column(String(3), nullable=False)


class FileQueue(base):
    """ORM for the ``file_queue`` table"""

    __tablename__ = 'file_queue'
    __table_args__ = (UniqueConstraint('queueid', 'subscriber_name', 'fileid', name='file_queue_uc'),)

    # Define the columns
    queueid = Column(Integer, primary_key=True)
    subscriber_name = Column(String(255), nullable=False)
    fileid = Column(Integer, nullable=False)
    entry_date = Column(String(10), nullable=False)
    expires = Column(String(10), nullable=False)


class Transactions(base):
    """ORM for the ``transaction_log`` table"""

    __tablename__ = 'transactions'

    # Define the columns
    transactionid = Column(Integer, primary_key=True)
    action = Column(String(255), nullable=False)
    subscriber_name = Column(String(255), nullable=False)
    start_time = Column(String(19), nullable=False)
    fileid = Column(Integer)
    source = Column(String(255))
    destination = Column(String(255))
    end_time = Column(String(19))
    complete = Column(Boolean)
