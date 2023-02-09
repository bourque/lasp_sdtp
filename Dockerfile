FROM python:3.9-alpine

RUN apk update
RUN apk add --no-cache gcc g++ musl-dev gcompat libc6-compat libaio py3-numpy
ENV PYTHONPATH=/usr/lib/python3.9/site-packages

WORKDIR /root
COPY . .

# Set up directories for testing
RUN mkdir test_subscriber_queues/
RUN mkdir test_subscriber_queues/prod/
RUN mkdir test_subscriber_queues/dev/

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
RUN pip install pipx
RUN pipx install poetry
RUN /root/.local/pipx/venvs/poetry/bin/poetry install

CMD ["sleep", "600"]