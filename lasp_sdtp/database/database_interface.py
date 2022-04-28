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

import glob
import os
import random
import string
import sys

from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import Float
from sqlalchemy import Identity
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Sequence
from sqlalchemy import String
from sqlalchemy import Table
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
    id_seq = Sequence('id_seq')

    # Define the columns
    fileid = Column(Integer, id_seq, server_default=id_seq.next_value(), primary_key=True)
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
    #id_seq = Sequence('id_seq')

    # Define the columns
    queueid = Column(Integer, Identity(start=1), primary_key=True)
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


def _get_checksum():
    """Return a randomly generated checksum

    Returns
    -------
    checksum : str
        A randomly generated checksum based on the ``checksum_type`` given in
        the system configuration
    """

    checksum_type = config['checksum_type']
    checksum_string = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(64))
    checksum = f'{checksum_type}:{checksum_string}'

    return checksum


def _get_shortname(filename):
    """Return the appropriate ``ShortName`` for the given filename.

    Parameters
    ----------
    filename : str
        The filename of interest (e.g. ``tsis2_tim_L2_v01_20220422.zip``)

    Returns
    -------
    shortname : str
        The ``ShortName`` that matches the given filename (e.g. ``TSIS2_TIM_L2``)
    """

    shortname_mapping = {
        'tsis2_L1': 'TSIS2_L1',
        'tsis2_sim_cal': 'TSIS2_SIM_CAL',
        'tsis2_tim_cal': 'TSIS2_TIM_CAL',
        'tsis2_sim_L2': 'TSIS2_SIM_L2',
        'tsis2_tim_L2': 'TSIS2_TIM_L2',
        'tsis2_sc_L2': 'TSIS_SC_L2',
        'tsis2_ssi_L3_c12h': 'TSIS2_SSI_L3_12HR',
        'tsis2_ssi_L3_c24h': 'TSIS2_SSI_L3_24HR',
        'tsis2_tsi_L3_c06h': 'TSIS2_TSI_L3_06HR',
        'tsis2_tsi_L3_c24h': 'TSIS2_TSI_L3_24HR'
    }

    for item in shortname_mapping:
        if filename.startswith(item):
            shortname = shortname_mapping[item]
            if filename.endswith('.txt'):
                shortname += '_TXT'
            elif filename.endswith('.nc'):
                shortname += '_NC'

    return shortname


def insert_test_data():
    """Insert test data into the test database. The data that are insterted is
    based on which files exist in the ``test_filesystem``
    """

    table = Table('file_metadata', base.metadata)
    test_filesystem = f'{HOME_DIR}/Desktop/test_filesystem/'
    test_files = glob.glob(os.path.join(test_filesystem, '*'))

    data_to_insert = []
    for i, test_file in enumerate(test_files):
        data = {
            'fileid': i + 1,
            'name': os.path.basename(test_file),
            'checksum': _get_checksum(),
            'size': os.path.getsize(test_file),
            'expires': '2022-12-31',
            'stream': 'prod',
            'shortname': _get_shortname(os.path.basename(test_file)),
            'version': '001'
        }
        data_to_insert.append(data)

    table.insert().execute(data_to_insert)


if __name__ == '__main__':

    if len(sys.argv) > 1 and sys.argv[1] == 'reset':
        print('Resetting database')
        base.metadata.drop_all()

    base.metadata.create_all(engine)
    insert_test_data()
