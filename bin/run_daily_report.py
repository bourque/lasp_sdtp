"""This script performs system reporting for the  application.  When executed,
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

TODO: Fix generate_daily_report to actually send an email
"""

from lasp_sdtp.utils.reporting import generate_daily_report

if __name__ == '__main__':

    generate_daily_report()
