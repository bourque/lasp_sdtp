"""This module is used to define the LASP SDTP application database ORMs. Each
class within corresponds to a database table.

Authors
-------
    - Matthew Bourque

Use
---

    The classes within are intended to be imported by the ``database_controller``
    module, e.g.:
    ::

        from lasp_sdtp.database import database_interface
        database_interface.Accounts
"""

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Accounts(Base):
    """ORM for the ``accounts`` table"""

    __tablename__ = 'accounts'
    __table_args__ = (UniqueConstraint('userid', 'username', 'certuid', name='accounts_uc'),)

    userid = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    certuid = Column(String(20), unique=True, nullable=False)
    role = Column(Enum('admin', 'subscriber', name='role'), nullable=False)
    registration_date = Column(DateTime, nullable=False)
    registration_expires = Column(DateTime)


class FileMetadata(Base):
    """ORM for the ``file_metadata`` table"""

    __tablename__ = 'file_metadata'
    __table_args__ = (UniqueConstraint('fileid', 'name', 'checksum', name='file_metadata_uc'),)

    fileid = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    checksum = Column(String(71), unique=True, nullable=False)
    size = Column(Float, nullable=False)
    expires = Column(DateTime, nullable=False)
    stream = Column(String(255), nullable=False)
    shortname = Column(String(255), nullable=False)
    version = Column(String(3), nullable=False)
    date = Column(DateTime, nullable=False)


class FileQueue(Base):
    """ORM for the ``file_queue`` table"""

    __tablename__ = 'file_queue'
    __table_args__ = (UniqueConstraint('queueid', 'username', 'fileid', name='file_queue_uc'),)

    queueid = Column(Integer, primary_key=True)
    username = Column(String(30), nullable=False)
    fileid = Column(Integer, nullable=False)
    entry_date = Column(DateTime, nullable=False)
    expires = Column(DateTime, nullable=False)


class Transactions(Base):
    """ORM for the ``transactions`` table"""

    __tablename__ = 'transactions'

    transactionid = Column(Integer, primary_key=True)
    action = Column(String(255), nullable=False)
    username = Column(String(30), nullable=False)
    start_time = Column(DateTime, nullable=False)
    fileid = Column(Integer)
    source = Column(String(255))
    destination = Column(String(255))
    end_time = Column(DateTime)
