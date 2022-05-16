"""Tests for ``reporting.py``

Authors
-------
    Matthew Bourque

Use
---
    pytest test_reporting.py
"""

import datetime

from lasp_sdtp.database.database_interface import Accounts
from lasp_sdtp.database.database_interface import insert_data
from lasp_sdtp.database.database_interface import session
from lasp_sdtp.utils.reporting import generate_daily_report


class TestReporting():
    """Tests for the ``reporting`` module"""

    def setup(self, test_method):
        """Method for setting up database entries for use in testing"""

        # Add a few accounts entries
        data = [
            {
                'username': 'test_reporting1',
                'certuid': 'test_cert1',
                'role': 'subscriber',
                'registration_date': datetime.datetime.today(),
                'registration_expires': datetime.datetime.today() + datetime.timedelta(days=1)
            },
            {
                'username': 'test_reporting2',
                'certuid': 'test_cert2',
                'role': 'subscriber',
                'registration_date': datetime.datetime.today(),
                'registration_expires': datetime.datetime.today() + datetime.timedelta(days=1)
            }

        ]
        insert_data('accounts', data)

    def test_generate_daily_report(self):
        """Tests the ``generate_daily_report`` function"""

        content_dict = generate_daily_report()

        # Check that the individal reports are in the content
        for content_type in ['active_subscribers']:
            assert content_type in content_dict

    def teardown(self, test_method):
        """Method for removing database entries that were used for testing"""

        # Remove entries that were added
        session.query(Accounts).filter(Accounts.username == 'test_reporting1').delete()
        session.query(Accounts).filter(Accounts.username == 'test_reporting2').delete()
        session.commit()
