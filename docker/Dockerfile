FROM python:3.9-buster AS base

RUN apt-get update
RUN apt-get install -y nano libffi-dev libaio1

# Needed to silence sqlalchemy>2.0 warnings, not needed since <2.0 is pinned
ENV SQLALCHEMY_SILENCE_UBER_WARNING=1

WORKDIR /root
COPY .. .

# Install and configure Oracle instantclient
RUN wget https://download.oracle.com/otn_software/linux/instantclient/193000/instantclient-basic-linux.x64-19.3.0.0.0dbru.zip
RUN unzip instantclient-basic-linux.x64-19.3.0.0.0dbru.zip
RUN cp -r instantclient_19_3/* /lib
RUN rm -fr instantclient-basic-linux.x64-19.3.0.0.0dbru.zip
RUN rm -fr instantclient_19_3/
RUN ln -s /usr/lib/libnsl.so.3 /usr/lib/libnsl.so.1
RUN ln -s /lib/libc.so.6 /usr/lib/libresolv.so.2

# Install package dependencies
RUN pip install --upgrade pip
RUN pip install poetry
RUN poetry install

# Set up directories for testing
RUN mkdir test_subscriber_queues/
RUN mkdir test_subscriber_queues/ges_disc/
RUN mkdir test_subscriber_queues/ges_disc/prod/
RUN mkdir test_subscriber_queues/ges_disc/dev/

# Create a test filesystem
RUN poetry run python bin/create_test_filesystem.py

# Keep the container running so it can be logged into
CMD ["sleep", "infinity"]