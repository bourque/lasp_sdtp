# The LASP SDTP Application


The Laboratory for Atmospheric and Space Physics (LASP) Standard Data Transfer Protocol (SDTP) Application is used to transfer LASP-based data products to the Goddard Earth Sciences Data Information Services (GES DISC).

More information can be found here: https://confluence.lasp.colorado.edu/pages/viewpage.action?pageId=86215664


## Installation


### Prerequisites

It is suggested that contributors have a working installation of `anaconda` or `miniconda` for Python 3.9.  Downloads and installation instructions are  available here:

- [Miniconda](https://conda.io/miniconda.html)
- [Anaconda](https://www.continuum.io/downloads)

Requirements for the `lasp_sdtp` package will be included in the `lasp-sdtp` `conda` environment, which is included in the installation instructions below.


### Clone the `lasp_sdtp` repository

Clone the current version of `lasp_sdtp` from the BitBucket repository:

```
git clone https://bitbucket.lasp.colorado.edu/scm/sds/lasp_sdtp.git
```

or, if you would rather use `SSH` instead of `https`, use

```
git clone ssh://git@bitbucket.lasp.colorado.edu:2222/sds/lasp_sdtp.git
```


### Environment Installation

Install the `lasp-sdtp` `conda` environment via the `environment.yml` file, which contains all of the dependencies needed for the application:

```
cd lasp_sdtp/
conda env create -f environment.yml
```


### Configuration Files

Fill out the ``admin_config.json`` and ``subscriber_config.json`` files appropriately.  The values within these files are used by the application to define and apply necessary configurations.  A description of each field is given below:



`admin_config.json`:

```python
{
	"db_connection_string": "oracle://server:username@database:port/?service_name=service",  # Connection string to Oracle database
	"email_address": "email@example.com",  # Email address from which daily reports are sent
	"email_password": "password",  # Email address password
	"endpoint": "0.0.0.0",  # Endpoint from which the server is hosted
	"filesystem_loc": "path/to/filesystem",  # Path to the parent directory of LAN filesystem
	"data_cache_loc": "path/to/data_cache/"  # Path to parent directory of data cache
}
```


`subscriber_config.json`:

```python
{
	"account_expiration_period": 1800,  # Subscriber account expiration period (in days)
	"checksum_type": "sha256",  # Checksum type
	"expiration_period": 180,  # Expiration period for files in data cache (in days)
	"max_num_files": 10000,  # Maximum number of files to return in GET /files request
	"num_download_threads": 5,  # Maximum number of simultaneous downloads
	"username": "username"  # Subscriber username
}
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
