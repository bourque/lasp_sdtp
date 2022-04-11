"""The main module for running the last_sdtp flask application

Authors
-------
	Matthew Bourque

Use
---

	To run a local server, run 'python app.py'
"""

from flask import Flask
from flask import request

app = Flask(__name__)

@app.route('/sdtp/v1/files', methods=['GET'])
def get_fieldlist():
	shortname = request.args.get('ShortName', default="foo", type=str)
	print(shortname)

@app.route('/sdtp/v1/files/<fileid>', methods=['GET'])
def get_files(file_id):
	pass

@app.route('/sdtp/v1/register', methods=['PUT'])
def register():
	pass

@app.route('/sdtp/v1/files/<fileid>', methods=['DELETE'])
def delete_file(file_id):
	pass

@app.route('/')
def home():
	pass

if __name__ == '__main__':

	app.run(host='0.0.0.0', port='8000')