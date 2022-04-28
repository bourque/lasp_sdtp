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

import os

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

# class TransactionLog(base):
#     """ORM for the ``transaction_log`` table"""

#
#     __tablename__ = 'transaction_log'

#     # Define the columns
#     transaction_id
#     subscriber_id
#     provider_id
#     start_time
#     end_time
