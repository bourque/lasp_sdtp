# The LASP SDTP Application


The Laboratory for Atmospheric and Space Physics (LASP) Science Data Transfer Protocol (SDTP) Application is used to
transfer LASP-based data products to the Goddard Earth Sciences Data Information Services (GES DISC).

This README covers the installation and usage of the application and is geared towards internal LASP developers and/or
contributors of this application.  More information about the design and implementation of the application can be found
here: https://confluence.lasp.colorado.edu/pages/viewpage.action?pageId=86215664


## Installation


### Prerequisites

It is suggested that developers have a working installation of `poetry` for Python 3.9.  Downloads and installation
instructions for `poetry` are available [here](https://python-poetry.org/docs/).

Requirements for the `lasp_sdtp` package will be included in the `lasp-sdtp` `poetry` environment, which is included
in the installation instructions below.


### Clone the `lasp_sdtp` repository

Clone the current version of `lasp_sdtp` from the BitBucket repository:

```
git clone https://bitbucket.lasp.colorado.edu/scm/sds/lasp_sdtp.git
```


### Environment Installation

Install and activate the `lasp-sdtp` `poetry` environment via the `pyproject.toml` file, which contains all the
dependencies needed for the application:

```
cd lasp_sdtp/
poetry install
```

To activate the environment:

```
poetry shell
```

### Configuration Files

Fill out the ``admin_config.json`` and ``subscriber_config.json`` files appropriately.  The values within these files
are used by the application to define and apply necessary configurations.  A description of each field is given below:



`admin_config.json`:

```python
{
    "api_endpoint": "http://127.0.0.1",  # URL for main enpoint of application
    "certificate_authority": "sample_certificate",  #  Certificate authority for authorization
    "db_connection_string": "oracle://server:username@database:port/?service_name=service",  # Connection string to Oracle database
    "email_address": "email@example.com",  # Email address from which daily reports are sent
    "email_password": "password",  # Email address password
    "email_port": 123,  # Email port number
    "email_server": "smtp.email.com",  # Email server
    "filesystem_loc": "/path/to/filesystem/",  # Path to where files can be ingested,
    "queue_api_port": 123,  # Port for queue API endpoint
    "request_api_port": 123,  # Port for request API endpoint
    "sdtp_api_port": 123,  # Port for SDTP API endpoint
    "staging_loc": "path/to/data_cache/"  # Path to parent directory of data cache
}
```

`subscriber_config.json`:

```python
{
    "checksum_type": "sha256",  # Checksum type
    "distinguished_name": "",  # Distinguished name for subscriber authentication
    "expiration_period": 180,  # Expiration period for files in data cache (in days)
    "max_num_files": 10000,  # Maximum number of files to return in GET /files request
    "missions": ['TSIS', 'TSIS2'],  # List of missions that subscriber is subscribed to
    "num_download_threads": 5,  # Maximum number of simultaneous downloads
    "username": "username",  # Subscriber username
    "streams": {  # Individual streams, with their supported tags & extras and their data types & default values
        "prod": {
            "extras": {
                "aperture": {
                    "type": "str",
                    "default": ""
                }
            },
            "tags": {
                "observation_date": {
                    "type": "str",
                    "default": ""
                }
            }
        },
        "dev": {
            "extras": {
                "was_extrapolated": {
                    "type": "bool",
                    "default": ""
                }
            },
            "tags": {
                "irradiance": {
                    "type": "float",
                    "default": ""
                }
            }
        }
    }
}
```

## Usage

To start the necessary servers:

```
cd bin/
python run_sdtp_servers.py
```

When the server is started, a log file is initialized (the path to which is printed to the terminal).  This log file
records various environment information and server activity.

## Testing

To run the `pytest` testing suite:

```
cd tests/
pytest -s .
```

Once the server is running and test data have been added, one can send requests to the server, e.g.:

```bash
curl -X GET "http://localhost:8000/files" -H "Accept: application/json" -H "Cert-UID: ges_disc_cert"
curl -X GET "http://localhost:8000/files?stream=prod&shortname=TSIS2_L1" -H "Accept: application/json" -H "Cert-UID: ges_disc_cert"
curl -X GET "http://localhost:8000/files/{fileid}" -H "Accept: application/json" -H "Cert-UID: ges_disc_cert"
curl -X DELETE "http://localhost:8000/files/{fileid}" -H "Accept: application/json" -H "Cert-UID: ges_disc_cert"
curl -X DELETE "http://localhost:8000/files/{fileid_start}-{fileid_end}" -H "Accept: application/json" -H "Cert-UID: ges_disc_cert"
```

To get a list of all the available `fileid`s (convenience for testing out `curl` commands):

```bash
curl -X GET "http://localhost:8000/files" "Accept: application/json" -H "Cert-UID: ges_disc_cert" | grep 'fileid'
```

## Contributions

To contribute to this repository:

1. Create a `feature-branch` off of the `main` branch.
2. Make software changes via the nominal `git add`/`git commit` workflow.
3. Push the `feature-branch` to the remote repository (i.e. `git push origin feature-branch`).
4. Create a pull request that merges the `feature-branch` into the `main` branch.
5. Assign a reviewer from the team for the pull request.
6. Iterate with the reviewer over any needed changes until the reviewer accepts and merges the branch.


## Issue Reporting / Feature Requests

Users who wish to report an issue or request a new feature may do so by submitting a new ticket on Jira: https://jira.lasp.colorado.edu/projects/TIMDS/issues
