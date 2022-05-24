from setuptools import setup
from setuptools import find_packages

REQUIRES = [
    'flask',
    'pandas',
    'pytest',
    'sqlalchemy'
]

setup(
    name='lasp_sdtp',
    version='0.0.0',
    description='Implementation of the NASA Standard Data Transfer Protocol (SDTP) Interface for LASP-based applications',
    url='https://bitbucket.lasp.colorado.edu/scm/sds/lasp_sdtp.git',
    author='Matthew Bourque',
    author_email='matthew.bourque@lasp.colorado.edu',
    packages=find_packages(),
    install_requires=REQUIRES,
    include_package_data=True
)
