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

import sys

from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


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

    connection_string = 'sqlite://///Users/mabo8927/Desktop/lasp_sdtp_db.db'
    engine = create_engine(connection_string, echo=True)
    base = declarative_base(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    meta = MetaData(engine)

    return session, base, engine, meta


# Define a global session so that it can easily be imported
session, base, engine, meta = load_connection()


class FileMetadata(base):
    """ORM for the ``file_metadata`` table"""

    # Name the table
    __tablename__ = 'file_metadata'

    # Define the columns
    fileid = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, unique=True, nullable=False)
    checksum = Column(String, unique=True, nullable=False)
    size = Column(Float, nullable=False)
    expires = Column(String, nullable=False)
    stream = Column(String, nullable=False)
    shortname = Column(String, nullable=False)
    version = Column(String, nullable=False)


def insert_test_data():
    """
    """

    table = Table('file_metadata', base.metadata, autoload=True)
    data = [
        {"fileid": 1234,
         "name": "tsis2_L1_20220413.zip",
         "checksum": "sha256:ca7316a6bdba23870508ae72c53872bfc0a87520cbe3a88679130a81f400d5ae",
         "size": 1,
         "expires": "2022-12-31",
         "stream": "prod",
         "shortname": "TSIS2_L1",
         "version": "001"},
        {"fileid": 5678,
         "name": "tsis2_L1_20220414.zip",
         "checksum": "sha256:3sesc1w9clz6amp42jryfybwtvoq9uk7gscf99o6zum6jsqfgr26x4cve52lk8ia",
         "size": 10,
         "expires": "2022-12-31",
         "stream": "prod",
         "shortname": "TSIS2_L1",
         "version": "001"},
        {"fileid": 9012,
         "name": "tsis2_L1_20220415.zip",
         "checksum": "sha256:cngw4694ii4gedgxkfgybvngevyc4dc4j9t2ewngyo2s2kcz8aq0935r07eazjxe",
         "size": 100,
         "expires": "2022-12-31",
         "stream": "prod",
         "shortname": "TSIS2_L1",
         "version": "001"},
        {"fileid": 3456,
         "name": "tsis2_tim_L2_v01_20220416.zip",
         "checksum": "sha256:dfl0lgwpjl0lt5hw0rljpa5ybvqbsq0du4ebhauos9qsisuy339ss21ovyjcdwh1",
         "size": 1000,
         "expires": "2023-01-01",
         "stream": "prod",
         "shortname": "TSIS2_TIM_L2",
         "version": "001"},
        {"fileid": 7890,
         "name": "tsis2_tim_L2_v01_20220417.zip",
         "checksum": "sha256:97r21sfc81yvfbo35s8fksouvkjjly3z445xql5cdjg0snrc1ukgaayq53x5ciro",
         "size": 10000,
         "expires": "2023-01-01",
         "stream": "prod",
         "shortname": "TSIS2_TIM_L2",
         "version": "001"}
    ]

    table.insert().execute(data)


if __name__ == '__main__':

    if len(sys.argv) > 1 and sys.argv[1] == 'reset':
        print('Resetting database')
        base.metadata.drop_all()

    base.metadata.create_all(engine)
    insert_test_data()
