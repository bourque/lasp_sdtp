"""Tests for ``reporting.py``

Authors
-------
    Matthew Bourque

Use
---
    pytest test_reporting.py
"""

from lasp_sdtp.utils.reporting import generate_daily_report


def test_generate_daily_report():
    """Tests the ``generate_daily_report`` function"""

    content_dict = generate_daily_report()

    # Check that the individal reports are in the content
    for content_type in ['active_subscribers', 'file_queue_contents', 'recent_transactions']:
        assert content_type in content_dict
