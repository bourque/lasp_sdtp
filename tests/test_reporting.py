"""Tests for the ``reporting.py`` module

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_reporting.py
"""

from lasp_sdtp.utils.reporting import generate_daily_report


def test_generate_daily_report():
    """Tests the ``generate_daily_report`` function"""

    # Generate the report
    content = generate_daily_report()

    content_list = [
        '<h2>Active Subscribers</h2>',
        '<h2>Recent Transactions</h2>',
        '<h2>File Queue Contents</h2>',
        '<h2>Long Transfers</h2>',
        '<h2>Expiring Files</h2>',
        '<h2>Expiring Accounts</h2>']

    # Check that the individal report sections are in the content
    for content_type in content_list:
        assert content_type in content
