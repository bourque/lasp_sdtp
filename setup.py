from setuptools import setup
from setuptools import find_packages

VERSION = '0.0'
AUTHORS = 'Matthew Bourque'
DESCRIPTION = ''

REQUIRES = [
    'flask',
    'pytest'
]

setup(
    name='lasp_sdtp',
    version=VERSION,
    description=DESCRIPTION,
    url='https://bitbucket.lasp.colorado.edu/scm/sds/lasp_sdtp.git',
    author=AUTHORS,
    author_email='matthew.bourque@lasp.colorado.edu',
    packages=find_packages(),
    install_requires=REQUIRES,
    include_package_data=True
)
