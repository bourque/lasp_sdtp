"""Various functions to enable system reporting for the ``lasp_sdtp``
application

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
from lasp_sdtp.database.database_interface import session


def _get_active_subscribers(content_dict):
    """Return email content to report on active subscribers

    Parameters
    ----------
    content_dict : dict
        A dictionary containing various content to add to the
        ``email_template.html``

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


def _send_email(content_dict):
    """Construct the final report email and send it

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

    return content


def generate_daily_report():
    """Creates a daily email report of system metrics"""

    content_dict = {}

    # Report active subscribers
    content_dict['active_subscribers'] = _get_active_subscribers(content_dict)

    # Report the current files in the queue

    # Report the transactions that happened in the past 24 hours

    # Report on available files

    # Send the email
    _send_email(content_dict)

    return content_dict


if __name__ == '__main__':

    generate_daily_report()
