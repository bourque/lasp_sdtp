"""This script performs system reporting for the application.  When executed,
an email is constructed and sent to the email provided in the
``admin_config.json`` file.  The email contains a daily report of information
about the system and its usage.

Authors
-------
    Matthew Bourque

Use
---
    This module is intended to be executed via the command line as such:
    ::
        python daily_report.py

TODO[1997]: Fix _send_email to actually send an email
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd
from jinja2 import Template
from sqlalchemy.orm.query import Query

from lasp_sdtp.config import admin_config
from lasp_sdtp.database.queries import get_report_queries


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


def _send_email(content: str):
    """Construct the final report email and send it.

    Parameters
    ----------
    content : str
        The content to add to ``email_template.html``
    """

    # Get the template
    email_template_file = Path(__file__).parent.parent / 'lasp_sdtp/utils/' / 'email_template.html'
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

    queries = get_report_queries()

    # Construct the email content for each of the queries
    content = ''
    for header, query in queries:
        content += _construct_content(header, query)

    # Send the email
    _send_email(content)

    return content


if __name__ == '__main__':

    generate_daily_report()
