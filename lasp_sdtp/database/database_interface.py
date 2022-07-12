"""This module is used to define the ``lasp_sdtp`` database ORMs. Each class
within corresponds to a database table.

Authors
-------
    - Matthew Bourque

Use
---

    The classes within are intended to be imported by the
    ``database_controller`` module, e.g.:
    ::

        from lasp_sdtp.database import database_interface
        database_interface.Accounts
"""

import sqlalchemy as sa

Base = sa.ext.declarative.declarative_base()


class Accounts(Base):
    """ORM for the ``accounts`` table"""

    __tablename__ = 'accounts'
    __table_args__ = (sa.UniqueConstraint('username', 'certuid', name='accounts_uc'),)

    username = sa.Column(sa.String(255), primary_key=True)
    certuid = sa.Column(sa.String(20), unique=True, nullable=False)
    role = sa.Column(sa.Enum('admin', 'subscriber', name='role'), nullable=False)
    registration_date = sa.Column(sa.DateTime, nullable=False)
    registration_expires = sa.Column(sa.DateTime)


class FileMetadata(Base):
    """ORM for the ``file_metadata`` table"""

    __tablename__ = 'file_metadata'
    __table_args__ = (sa.UniqueConstraint('fileid', 'name', 'checksum', name='file_metadata_uc'),)

    fileid = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(255), unique=True, nullable=False)
    checksum = sa.Column(sa.String(71), unique=True, nullable=False)
    size = sa.Column(sa.Float, nullable=False)
    expires = sa.Column(sa.DateTime, nullable=False)
    stream = sa.Column(sa.String(255), nullable=False)
    shortname = sa.Column(sa.String(255), nullable=False)
    version = sa.Column(sa.String(3), nullable=False)
    date = sa.Column(sa.DateTime, nullable=False)


class FileQueue(Base):
    """ORM for the ``file_queue`` table"""

    __tablename__ = 'file_queue'
    __table_args__ = (sa.UniqueConstraint('queueid', 'username', 'fileid', name='file_queue_uc'),)

    queueid = sa.Column(sa.Integer, primary_key=True)
    username = sa.Column(sa.String(30), nullable=False)
    fileid = sa.Column(sa.Integer, nullable=False)
    entry_date = sa.Column(sa.DateTime, nullable=False)
    expires = sa.Column(sa.DateTime, nullable=False)


class Transactions(Base):
    """ORM for the ``transactions`` table"""

    __tablename__ = 'transactions'

    transactionid = sa.Column(sa.Integer, primary_key=True)
    action = sa.Column(sa.String(255), nullable=False)
    username = sa.Column(sa.String(30), nullable=False)
    start_time = sa.Column(sa.DateTime, nullable=False)
    fileid = sa.Column(sa.Integer)
    source = sa.Column(sa.String(255))
    destination = sa.Column(sa.String(255))
    end_time = sa.Column(sa.DateTime)
