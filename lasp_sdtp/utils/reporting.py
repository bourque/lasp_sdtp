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
import os
import smtplib

import pandas as pd

from lasp_sdtp.config import admin_config
from lasp_sdtp.database.database_interface import Accounts
from lasp_sdtp.database.database_interface import FileMetadata
from lasp_sdtp.database.database_interface import FileQueue
from lasp_sdtp.database.database_interface import session
from lasp_sdtp.database.database_interface import Transactions


def _active_subscribers_report():
    """Return email content to report on currently active subscribers

    Returns
    -------
    content : str
        HTML code to be rendered in the report email
    """

    # Get list of active accounts
    query = session.query(Accounts.userid, Accounts.username, Accounts.registration_date, Accounts.registration_expires) \
        .filter(Accounts.role == 'subscriber') \
        .filter(Accounts.registration_expires >= datetime.datetime.today())

    # Store results as an HTML table
    results = pd.read_sql(query.statement, query.session.bind).to_html(index=False)

    # Construct HTML content
    content = '<h2>Active Subscribers</h2><br>'
    content += results

    return content


def _file_queue_report():
    """Return email content to report on the current contents of the file queue

    Returns
    -------
    content : str
        HTML code to be rendered in the report email
    """

    # Get list of files in the queue
    query = session.query(FileQueue.queueid, FileQueue.fileid, FileMetadata.name, FileQueue.username, FileQueue.entry_date, FileQueue.expires) \
        .select_from(FileMetadata) \
        .join(FileQueue, FileMetadata.fileid == FileQueue.fileid) \
        .filter(FileQueue.expires >= datetime.datetime.today())

    # Store results as an HTML table
    results = pd.read_sql(query.statement, query.session.bind).to_html(index=False)

    # Construct HTML content
    content = '<h2>File Queue</h2><br>'
    content += results

    return content


def _recent_transactions_report():
    """Return email content to report on transactions that occurred within the
    last 24 hours

    Returns
    -------
    content : str
        HTML code to be rendered in the report email
    """

    # Get list of recent transcations
    query = session.query(Transactions.transactionid, Transactions.action, Transactions.username, FileMetadata.name, Transactions.start_time,
                          Transactions.end_time, Transactions.source, Transactions.destination) \
        .join(Transactions, FileMetadata.fileid == Transactions.fileid)

    # Store results as an HTML table
    results = pd.read_sql(query.statement, query.session.bind).to_html(index=False)

    # Construct HTML content
    content = '<h2>Recent Transactions</h2><br>'
    content += results

    return content


def send_email(content_dict):
    """Construct the final report email and send it.

    Parameters
    ----------
    content_dict : dict
        A dictionary containing various content to add to the
        ``email_template.html``
    """

    # Get the template
    email_template_file = os.path.join(os.path.dirname(__file__), 'email_template.html')
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


def generate_daily_report():
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

    # Send the email
    send_email(content_dict)

    return content_dict


if __name__ == '__main__':

    generate_daily_report()
