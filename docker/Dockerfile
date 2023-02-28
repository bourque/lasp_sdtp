FROM python:3.9-alpine AS base

RUN apk update
RUN apk add --no-cache curl gcc g++ musl-dev gcompat libc6-compat libaio py3-numpy

# Needed to use system install of numpy
ENV PYTHONPATH=/usr/lib/python3.9/site-packages

# Needed to silence sqlalchemy>2.0 warnings, not needed since <2.0 is pinned
ENV SQLALCHEMY_SILENCE_UBER_WARNING=1

WORKDIR /root
COPY .. .

# Install Oracle instantclient
RUN wget https://download.oracle.com/otn_software/linux/instantclient/193000/instantclient-basic-linux.x64-19.3.0.0.0dbru.zip
RUN unzip instantclient-basic-linux.x64-19.3.0.0.0dbru.zip
RUN cp -r instantclient_19_3/* /lib
RUN rm -rf instantclient-basic-linux.x64-19.3.0.0.0dbru.zip
RUN ln -s /usr/lib/libnsl.so.3 /usr/lib/libnsl.so.1
RUN ln -s /lib/libc.so.6 /usr/lib/libresolv.so.2

# Install package dependencies
RUN pip install --upgrade pip
#RUN ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future pip install --upgrade numpy
RUN pip install poetry
RUN poetry install

CMD ["sleep", "6000"]

FROM base AS test

# Set up directories for testing
RUN mkdir test_subscriber_queues/
RUN mkdir test_subscriber_queues/test_account/
RUN mkdir test_subscriber_queues/test_account/prod/
RUN mkdir test_subscriber_queues/test_account/dev/

# Create a test filesystem
RUN poetry run python bin/create_test_filesystem.py