"""Various properties to help support the ``lasp_sdtp`` application.

Authors
-------
    Matthew Bourque

Use
---
    Variables within this module are intended to be imported and used within
    other modules, e.g.:
    ::
        from lasp_sdtp.utils.properties import TSIS2_SHORTNAMES
"""

LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'class': 'logging.Formatter',
            'format': '[%(asctime)s] %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S'
        },
        'detailed': {
            'class': 'logging.Formatter',
            'format': '[%(asctime)s %(name)s.%(funcName)s:%(lineno)i %(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'placeholder',
            'mode': 'a'
        }
    },
    'loggers': {
        'lasp_sdtp': {
            'level': 'DEBUG'
        },
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console', 'file']
    }
}

REQUIRED_ADMIN_CONFIG_KEYS = {
    'api_endpoint': str,
    'certificate_authority': str,
    'staging_loc': str,
    'db_connection_string': str,
    'email_address': str,
    'email_password': str,
    'email_port': int,
    'email_server': str,
    'endpoint': str,
    'filesystem_loc': str,
    'queue_api_port': int,
    'request_api_port': int,
    'sdtp_api_port': int
}

REQUIRED_SUBSCRIBER_CONFIG_KEYS = {
    'account_expiration_period': int,
    'checksum_type': str,
    'distinguished_name': str,
    'expiration_period': int,
    'max_num_files': int,
    'num_download_threads': int,
    'username': str,
    'streams': dict
}

# Files generated purely for tests that should be ignored in nominal GET /files requests
TEST_FILES_TO_IGNORE = [
    'test_cleanup_db.txt', 'test_cleanup_db2.txt', 'test_reporting.txt', 'test_db_controller.txt',
    'tsis2_L1_19840404.zip', 'tsis2_sim_cal_v01.zip', 'tsis2_sc_L2_v01_19840404_19840405.zip', 'insert_data.txt',
    'test_pagination_99990.txt', 'test_pagination_99991.txt', 'test_pagination_99992.txt',
    'test_pagination_99993.txt', 'test_pagination_99994.txt', 'test_pagination_99995.txt']

TSIS2_FILENAME_STRUCTURES = {
        'TSIS2_L1': 'tsis2_L1_<date>.zip',
        'TSIS2_SIM_CAL': 'tsis2_sim_cal_v01.zip',
        'TSIS2_TIM_CAL': 'tsis2_tim_cal_v01.zip',
        'TSIS2_SIM_L2': 'tsis2_sim_L2_v01_<date>.zip',
        'TSIS2_TIM_L2': 'tsis2_tim_L2_v01_<date>.zip',
        'TSIS2_SC_L2': 'tsis2_sc_L2_v01_<date>_<date2>.zip',
        'TSIS2_SSI_L3_12HR_TXT': 'tsis2_ssi_L3_c12h_v01_<date>_<date2>.txt',
        'TSIS2_SSI_L3_24HR_TXT': 'tsis2_ssi_L3_c24h_v01_<date>_<date2>.txt',
        'TSIS2_TSI_L3_06HR_TXT': 'tsis2_tsi_L3_c06h_v01_<date>_<date2>.txt',
        'TSIS2_TSI_L3_24HR_TXT': 'tsis2_tsi_L3_c24h_v01_<date>_<date2>.txt',
        'TSIS2_SSI_L3_12HR_NC': 'tsis2_ssi_L3_c12h_v01_<date>_<date2>.nc',
        'TSIS2_SSI_L3_24HR_NC': 'tsis2_ssi_L3_c12h_v01_<date>_<date2>.nc',
        'TSIS2_TSI_L3_06HR_NC': 'tsis2_tsi_L3_c06h_v01_<date>_<date2>.nc',
        'TSIS2_TSI_L3_24HR_NC': 'tsis2_tsi_L3_c24h_v01_<date>_<date2>.nc'
    }
