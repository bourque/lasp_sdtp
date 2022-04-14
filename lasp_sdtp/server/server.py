"""The main module for running the last_sdtp flask application

Authors
-------
	Matthew Bourque

Use
---

	To run a local server, use:
		FLASK_APP=server.py FLASK_ENV=development flask run --port 8000
"""

import glob
import os

from flask import Flask
from flask import request

app = Flask(__name__)

FILESYSTEM_PATH = '../test_filesystem/'

@app.route('/files', methods=['GET'])
def get_fieldlist():

	# Parse paramters from the request
	stream = request.args.get('stream', default=None, type=str)
	shortname = request.args.get('ShortName', default=None, type=str)

	# Determine which files to return based on parameters
	# Currently the files are gathered from a local filesystem
	# Eventually these may be retrieved via a database query
	if shortname:
		filepaths = glob.glob(os.path.join(FILESYSTEM_PATH, shortname, '*'))
	else:
		filepaths = glob.glob(os.path.join(FILESYSTEM_PATH, '*'))

	# Construct the response
	# Currently a hard-coded response is given that matches the SDTP protocol
	# Eventually these may be constructed based on models provided in models.py
	response = {
		"files": [
		{
	    	"fileid": 1342,
	    	"name": "tsis2_L1_20220412.zip",
	    	"checksum": "sha256:f4c96f1f144f083485e8a4ea490cb605a7d0f2ffb7a11ec48e97a9e1631aa079",
	    	"size": 5678,
	   		"expires": "2022-12-31",
	    	"tags": {
	      		"stream": "prod",
	      		"ShortName": "TSIS2_L1",
	      		"Version": "001"
	      	}
	    },
		{
	    	"fileid": 1355,
	    	"name": "tsis2_L1_20220413.zip",
	    	"checksum": "sha256:ca7316a6bdba23870508ae72c53872bfc0a87520cbe3a88679130a81f400d5ae",
	    	"size": 15,
	   		"expires": "2022-12-31",
	    	"tags": {
	      		"stream": "prod",
	      		"ShortName": "TSIS2_L1",
	      		"Version": "001"
	      	}
	    }]	      	
  	}
	response['status'] = 200
	
	return response


@app.route('/files/<fileid>', methods=['GET'])
def get_files(file_id):
	pass


@app.route('/register', methods=['PUT'])
def register():
	pass

@app.route('/files/<fileid>', methods=['DELETE'])
def delete_file(file_id):
	pass

@app.route('/')
def home():
	pass

if __name__ == '__main__':

	app.run(host='0.0.0.0', port='8000')
