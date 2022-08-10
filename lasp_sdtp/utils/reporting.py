"""Various functions to enable system reporting for the ``lasp_sdtp``
application.  When this module is executed, an email is constructed and sent
to the email provided in the ``admin_config.json`` file that contains
a daily report of information about the system.

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be run via the ``run_daily_report.py`` script:
    ::
        from lasp_sdtp.utils.reporting import generate_daily_report
        generate_daily_report()

TODO: Update email server to avoid using gmail
"""

import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd
from jinja2 import Template
from sqlalchemy.orm.query import Query

from lasp_sdtp.config import admin_config
from lasp_sdtp.database.database_controller import db


def _construct_content(header: str, query: Query) -> str:
    """Takes a query and turns it into an HTML table to render in the report
    email.

    Parameters
    ----------
    header: str
        A ``<h2>`` header to use for the content in the email
    query : ``sqlalchemy.orm.query.Query`` obj
        The query to use to generate the content

    Returns
    -------
    content : str
        HTML content to add to the report email
    """

    # Store query results as an HTML table
    results = pd.read_sql(query.statement, query.session.bind).to_html(index=False)

    # Construct HTML content
    content = f'<h2>{header}</h2><br>'
    content += results

    return content


def _get_report_queries() -> list:
    """Return a list of queries used to generate content for the report email

    Returns
    -------
    queries : list of ``sqlalchemy.orm.query.Query`` objects
    """

    # List to hold the queries
    queries = []

    # Active accounts
    queries.append((
        'Active Subscribers',
        db.session.query(
            db.Accounts.username, db.Accounts.registration_date, db.Accounts.registration_expires
        ).filter(
            db.Accounts.role == 'subscriber',
            db.Accounts.registration_expires >= datetime.datetime.utcnow().date())))

    # Recent transactions
    queries.append((
        'Recent Transactions',
        db.session.query(
            db.Transactions.transactionid, db.Transactions.action, db.Transactions.username, db.FileMetadata.name,
            db.Transactions.start_time, db.Transactions.end_time, db.Transactions.source, db.Transactions.destination
        ).join(
            db.Transactions, db.FileMetadata.fileid == db.Transactions.fileid)))

    # File queue contents
    queries.append((
        'File Queue Contents',
        db.session.query(
            db.FileQueue.queueid, db.FileQueue.fileid, db.FileMetadata.name, db.FileQueue.username, db.FileQueue.entry_date, db.FileQueue.expires
        ).select_from(
            db.FileMetadata
        ).join(
            db.FileQueue, db.FileMetadata.fileid == db.FileQueue.fileid
        ).filter(
            db.FileQueue.expires >= datetime.datetime.utcnow().date())))

    # Files that are taking too long
    queries.append((
        'Long Transfers',
        db.session.query(
            db.Transactions.transactionid, db.Transactions.action, db.Transactions.username, db.FileMetadata.name,
            db.Transactions.start_time, db.Transactions.end_time, db.Transactions.source, db.Transactions.destination
        ).join(
            db.Transactions, db.FileMetadata.fileid == db.Transactions.fileid
        ).filter(
            db.Transactions.end_time == None,
            db.Transactions.start_time <= datetime.datetime.utcnow() - datetime.timedelta(hours=24))))

    # Expiring files
    queries.append((
        'Expiring Files',
        db.session.query(
            db.FileQueue.queueid, db.FileQueue.fileid, db.FileMetadata.name, db.FileQueue.username, db.FileQueue.entry_date, db.FileQueue.expires
        ).select_from(
            db.FileMetadata
        ).join(
            db.FileQueue, db.FileMetadata.fileid == db.FileQueue.fileid
        ).filter(
            db.FileQueue.expires <= datetime.datetime.utcnow().date() + datetime.timedelta(days=7))))

    # Expiring accounts
    queries.append((
        'Expiring Accounts',
        db.session.query(
            db.Accounts.username, db.Accounts.registration_date, db.Accounts.registration_expires
        ).filter(
            db.Accounts.role == 'subscriber'
        ).filter(
            db.Accounts.registration_expires <= datetime.datetime.utcnow().date() + datetime.timedelta(days=30))))

    return queries


def _send_email(content: str):
    """Construct the final report email and send it.

    Parameters
    ----------
    content : str
        The content to add to ``email_template.html``
    """

    # Get the template
    email_template_file = Path(__file__).parent / 'email_template.html'
    with open(email_template_file) as f:
        template = Template(f.read())

    # Add content
    body = template.render(content=content)

    # Construct email message
    msg = MIMEMultipart()
    msg['Subject'] = 'LASP SDTP Daily Report'
    msg['From'] = admin_config['email_address']
    msg['To'] = 'matthew.bourque@lasp.colorado.edu'
    msg.attach(MIMEText(body, 'html'))

    # # Send the email
    # server = smtplib.SMTP(admin_config['email_server'], admin_config['email_port'])
    # server.starttls()
    # server.login(admin_config['email_address'], admin_config['email_password'])
    # text = msg.as_string()
    # server.sendmail(admin_config['email_address'], 'matthew,bourque@lasp.colorado.edu', text)
    # server.quit()


def generate_daily_report() -> str:
    """Creates a daily email report of system information

    Returns
    -------
    content : str
        The HTML content of the report email
    """

    queries = _get_report_queries()

    # Construct the email content for each of the queries
    content = ''
    for header, query in queries:
        content += _construct_content(header, query)

    # Send the email
    _send_email(content)

    return content
