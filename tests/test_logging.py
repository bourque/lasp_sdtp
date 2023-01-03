"""Tests for the ``logging.py`` module.

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
from pathlib import Path
from pathlib import PosixPath

from lasp_sdtp.utils.logging import _get_log_file
from lasp_sdtp.utils.logging import configure_logging
from lasp_sdtp.utils.properties import LOG_CONFIG


def test_configure_logging():
    """Tests the ``configure_logging`` function"""

    # Configure a log file
    log_file = configure_logging(Path.cwd(), verbose=False)

    # Perform some basic logging
    logging.debug('Some system information')
    logging.info('Some information for users')
    logging.warning('A warning')
    logging.critical('A critical error')

    # Check that the log file was created
    assert Path(log_file).exists

    # Open the log file and check the contents
    with open(log_file, 'r') as f:
        data = f.readlines()
    data = str([line.strip() for line in data])
    testable_content = ['User:', 'System:', 'Python Executable Path:', 'Conda Environment:', 'DEBUG', 'INFO', 'WARNING', 'CRITICAL']
    for item in testable_content:
        assert item in data

    # Remove the log file
    Path.unlink(log_file)


def test_get_log_file():
    """Tests the ``_get_log_file`` function"""

    log_file = _get_log_file(Path.cwd())

    assert isinstance(log_file, PosixPath)
    assert str(Path.cwd()) in str(log_file)
    assert str(log_file).endswith('.log')


def test_log_config():
    """Tests the ``log_config`` property"""

    assert isinstance(LOG_CONFIG, dict)
