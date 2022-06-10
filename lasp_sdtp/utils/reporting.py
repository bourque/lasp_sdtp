"""Various functions to enable system reporting for the ``lasp_sdtp``
application.  When this module is executed, an email is constructed and sent
to the email provided in the ``admin_config.json`` file that contains
a daily report of information about the system.

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be executed via the command line as such:
    ::
        python reporting.py
"""

import datetime
from email.message import EmailMessage
from pathlib import Path
import smtplib

import pandas as pd

from lasp_sdtp.config import admin_config
from lasp_sdtp.database.database_controller import db


def _active_subscribers_report() -> str:
    """Return email content to report on currently active subscribers

    Returns
    -------
    content : str
        HTML code to be rendered in the report email
    """

    # Get list of active accounts
    query = db.session.query(db.Accounts.userid, db.Accounts.username, db.Accounts.registration_date, db.Accounts.registration_expires) \
        .filter(db.Accounts.role == 'subscriber') \
        .filter(db.Accounts.registration_expires >= datetime.datetime.utcnow().date())

    # Store results as an HTML table
    results = pd.read_sql(query.statement, query.session.bind).to_html(index=False)

    # Construct HTML content
    content = '<h2>Active Subscribers</h2><br>'
    content += results

    return content


# def _expires_soon_report() -> str:
#     """Return email content to report on files and accounts that are about to
#     expire

#     Returns
#     -------
#     content : str
#         HTML code to be rendered in the report email
#     """

#     # Get list of accounts that are set to expire within a month


#     # Store results as an HTML table
#     results = pd.read_sql(query.statement, query.session.bind).to_html(index=False)

#     # Construct HTML content
#     content = '<h2>Active Subscribers</h2><br>'
#     content += results

#     return content


def _file_queue_report() -> str:
    """Return email content to report on the current contents of the file queue

    Returns
    -------
    content : str
        HTML code to be rendered in the report email
    """

    # Get list of files in the queue
    query = db.session.query(db.FileQueue.queueid, db.FileQueue.fileid, db.FileMetadata.name, db.FileQueue.username, db.FileQueue.entry_date, db.FileQueue.expires) \
        .select_from(db.FileMetadata) \
        .join(db.FileQueue, db.FileMetadata.fileid == db.FileQueue.fileid) \
        .filter(db.FileQueue.expires >= datetime.datetime.utcnow().date())

    # Store results as an HTML table
    results = pd.read_sql(query.statement, query.session.bind).to_html(index=False)

    # Construct HTML content
    content = '<h2>File Queue</h2><br>'
    content += results

    return content


def _recent_transactions_report() -> str:
    """Return email content to report on transactions that occurred within the
    last 24 hours

    Returns
    -------
    content : str
        HTML code to be rendered in the report email
    """

    # Get list of recent transcations
    query = db.session.query(db.Transactions.transactionid, db.Transactions.action, db.Transactions.username, db.FileMetadata.name, db.Transactions.start_time,
                          db.Transactions.end_time, db.Transactions.source, db.Transactions.destination) \
        .join(db.Transactions, db.FileMetadata.fileid == db.Transactions.fileid)

    # Store results as an HTML table
    results = pd.read_sql(query.statement, query.session.bind).to_html(index=False)

    # Construct HTML content
    content = '<h2>Recent Transactions</h2><br>'
    content += results

    return content


def send_email(content_dict: dict):
    """Construct the final report email and send it.

    Parameters
    ----------
    content_dict : dict
        A dictionary containing various content to add to the
        ``email_template.html``
    """

    # Get the template
    email_template_file = Path(__file__).parent / 'email_template.html'
    with open(email_template_file) as f:
        content = f.read().replace('\n', '')

    # Add to the content
    for content_name in content_dict:
        content = content.replace(f'<{content_name}_div>', content_dict[content_name])

    msg = EmailMessage()
    msg['Subject'] = 'LASP SDTP Daily Report'
    msg['From'] = 'test.tsis.tim@gmail.com'
    msg['To'] = 'matthew.bourque@lasp.colorado.edu'
    msg.set_content(content, subtype='html')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(admin_config['email_address'], admin_config['email_password'])
        smtp.send_message(msg)


def generate_daily_report() -> dict:
    """Creates a daily email report of system information

    Returns
    -------
    content_dict : dict
        A dictionary containing various content that was sent in the email
    """

    # Placeholder to store email content
    content_dict = {}

    # Report active subscribers
    content_dict['active_subscribers'] = _active_subscribers_report()

    # Report the current files in the queue
    content_dict['file_queue_contents'] = _file_queue_report()

    # Report the transactions that happened in the past 24 hours
    content_dict['recent_transactions'] = _recent_transactions_report()

    # # Report files that are about to expire
    # content_dict['expires_soon'] = _expires_soon_report()

    # Send the email
    #send_email(content_dict)

    return content_dict
