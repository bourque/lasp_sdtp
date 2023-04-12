"""This module is used to define the database ORMs. Each class within maps to a
table in the database.

The definitions within this module should have direct correspondence with the
Oracle-specific table definitions provided in ``sql/create.sql`` file.

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

Base = sa.orm.declarative_base()


class Accounts(Base):
    """ORM for the ``Accounts`` table"""

    __tablename__ = 'ACCOUNTS'

    username = sa.Column('username', sa.String(30), primary_key=True)
    role = sa.Column('role', sa.Enum('admin', 'subscriber', name='role'), nullable=False)
    registration_open = sa.Column('registrationopen', sa.Boolean, nullable=False)
    certuid = sa.Column('certuid', sa.String(20), unique=True)
    registration_date = sa.Column('registrationdate', sa.DateTime)
    registration_expires = sa.Column('registrationexpires', sa.DateTime)


class FileQueue(Base):
    """ORM for the ``FileQueue`` table"""

    __tablename__ = 'FILEQUEUE'

    username = sa.Column('username', sa.String(30), primary_key=True, nullable=False)
    fileid = sa.Column('fileid', sa.Integer, primary_key=True, nullable=False)
    entry_date = sa.Column('entrydate', sa.DateTime, nullable=False)
    expires = sa.Column('expires', sa.DateTime, nullable=False)


class Files(Base):
    """ORM for the ``Files`` table"""

    __tablename__ = 'FILES'
    __table_args__ = (sa.UniqueConstraint('fileid', 'name', 'checksum', name='file_metadata_uc'),)

    fileid = sa.Column('fileid', sa.Integer, primary_key=True)
    name = sa.Column('name', sa.String(255), unique=True, nullable=False)
    checksum = sa.Column('checksum', sa.String(71), unique=True, nullable=False)
    size = sa.Column('size', sa.Float, nullable=False)
    expires = sa.Column('expires', sa.DateTime, nullable=False)
    stream = sa.Column('stream', sa.String(255), nullable=False)
    shortname = sa.Column('shortname', sa.String(255), nullable=False)
    version = sa.Column('version', sa.String(5), nullable=False)
    ingest_date = sa.Column('ingestdate', sa.DateTime, nullable=False)
    available = sa.Column('available', sa.Boolean, nullable=False)
    deletion_date = sa.Column('deletiondate', sa.DateTime)


class MissionAccountMapping(Base):
    """ORM for the ``MissionAccountMapping`` table"""

    __tablename__ = 'MISSIONACCOUNTMAPPING'

    mission = sa.Column('mission', sa.String(30), primary_key=True)
    account = sa.Column('account', sa.String(30), primary_key=True)


class Missions(Base):
    """ORM for the ``Missions`` table"""

    __tablename__ = 'MISSIONS'
    __table_args__ = (sa.UniqueConstraint('mission', 'ingestdirectory', name='missions_uc'),)

    mission = sa.Column('mission', sa.String(30), primary_key=True)
    ingest_directory = sa.Column('ingestdirectory', sa.String(255), unique=True, nullable=False)


class MissionShortnameMapping(Base):
    """ORM for the ``MissionShortnameMapping`` table"""

    __tablename__ = 'MISSIONSHORTNAMEMAPPING'

    mission = sa.Column('mission', sa.String(30), primary_key=True)
    shortname = sa.Column('shortname', sa.String(255), primary_key=True)


class Shortnames(Base):
    """ORM for the ``Shortnames`` table"""

    __tablename__ = 'SHORTNAMES'

    shortname = sa.Column('shortname', sa.String(255), primary_key=True)
    filename_pattern = sa.Column('filenamepattern', sa.String(255), nullable=False)


class TagsAndExtras(Base):
    """ORM for the ``TagsAndExtras`` table"""

    __tablename__ = 'TAGSANDEXTRAS'

    fileid = sa.Column('fileid', sa.Integer, primary_key=True)
    field_name = sa.Column('fieldname', sa.String(255), primary_key=True)
    field_type = sa.Column('fieldtype', sa.Enum('tag', 'extra', name='fieldType'), primary_key=True)
    value = sa.Column('value', sa.String(255))


class Transactions(Base):
    """ORM for the ``Transactions`` table"""

    __tablename__ = 'TRANSACTIONS'

    transactionid = sa.Column('transactionid', sa.Integer, primary_key=True)
    action = sa.Column('action', sa.String(255), nullable=False)
    username = sa.Column('username', sa.String(30), nullable=False)
    start_time = sa.Column('starttime', sa.DateTime, nullable=False)
    fileid = sa.Column('fileid', sa.Integer)
    source = sa.Column('source', sa.String(255))
    destination = sa.Column('destination', sa.String(255))
    end_time = sa.Column('endtime', sa.DateTime)
    response_status = sa.Column('responsestatus', sa.String(255))
