"""Tests for the ``logging.py`` module

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_logging.py
"""

import logging
import os

from lasp_sdtp.utils.logging import configure


def test_configure():
    """Tests the ``configure`` function"""

    # Configure a log file
    log_file = configure(verbose=False)

    # Perform some basic logging
    logging.info('Some information')
    logging.warning('A warning')
    logging.critical('A critical error')

    # Check that the log file was created
    assert os.path.exists(log_file)

    # Open the log file and check the contents
    with open(log_file, 'r') as f:
        data = f.readlines()
    data = str([line.strip() for line in data])
    testable_content = ['User:', 'System:', 'Python Executable Path:', 'Conda Environment:', 'INFO:', 'WARNING:', 'CRITICAL:']
    for item in testable_content:
        assert item in data
