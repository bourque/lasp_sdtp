"""Tests for the ``utils.py`` module.

Authors
-------
    Matthew Bourque

Use
---
    To run these tests use:
    ::
        pytest -s test_utils.py

TODO: utils.py has changed a lot.  Make sure the tests here still make sense.
"""

import logging
from pathlib import Path

from lasp_sdtp.config import subscriber_config
from lasp_sdtp.utils.utils import configure_logging
from lasp_sdtp.utils.utils import get_checksum
from lasp_sdtp.utils.utils import get_shortname


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


def test_get_checksum():
    """Tests the ``get_checksum`` function"""

    checksum = get_checksum()

    # Check that the checksum type is correct
    assert checksum.split(':')[0] == subscriber_config['checksum_type']

    # Check that the checsum is of proper length
    assert len(checksum.split(':')[-1]) == 64


def test_get_shortname():
    """Tests the ``get_shortname`` function"""

    assert get_shortname('tsis2_L1') == 'TSIS2_L1'
