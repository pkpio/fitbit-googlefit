#!/usr/bin/env python
import httplib2
import sys
import time
import argparse
import logging
import datetime
import dateutil.tz
import dateutil.parser
import configparser
import json

import fitbit
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2Credentials
from googleapiclient.errors import HttpError


########################### Helper functions ############################
def GetFitbitClient(filepath):
	"""Returns an authenticated fitbit client object

	filepath -- path to file containing oauth credentials in json format
	"""
	logging.debug("Creating Fitbit client")
	credentials = json.load(open(filepath))  
	client = fitbit.Fitbit(**credentials)
	logging.debug("Fitbit client created")
	return client, credentials

def UpdateFitbitCredentials(fitbit_client, filepath, credentials):
	"""Persists new fitbit credentials to local storage

	fitbit_client -- fitbit client object that contains the latest credentials
	filepath -- path to file containing oauth credentials in json format
	credentails -- previous credentials object
	"""
	dump = False
	for t in ('access_token', 'refresh_token'):
		if client.client.token[t] != credentials[t]:
			credentials[t] = client.client.token[t]
			dump = True
	if dump:
		logging.debug("Updating Fitbit credentials")
		json.dump(credentials, open(filename, 'w'))

def GetGoogleClient(filepath):
	"""Returns an authenticated google fit client object

	filepath -- path to file containing oauth credentials in json format
	"""
	logging.debug("Creating Google client")
	credentials = Storage(filepath).get()
	http = credentials.authorize(httplib2.Http())
	client = build('fitness', 'v1', http=http)
	logging.debug("Google client created")
	return client

def GetDataSource():
	"""Returns a data source for Google Fit data logging"""
	return dict(
		type='raw',
		application=dict(name='fbit-gfit'),
		dataType=dict(name='com.google.step_count.delta',
			field=[dict(name='steps',format='integer')]),
		device=dict(type='watch',manufacturer='fitbit',model='charge-hr',
			uid='io.pkp.fbit-gfit',version='1'))

def GetDataSourceId(dataSource,credsFilepath):
	"""Returns a data source id for Google Fit

	dataSource -- dataSource object containing a dict of source identifiers
	credsFilepath -- path to file containing Google oauth credentials
	"""
	projectNumber = Storage(credsFilepath).get().client_id.split('-')[0]
	return ':'.join((
		dataSource['type'],
		dataSource['dataType']['name'],
		projectNumber,
		dataSource['device']['manufacturer'],
		dataSource['device']['model'],
		dataSource['device']['uid']))


#======================== Main application code =========================
def main():
	# Arguments parsing
	parser = argparse.ArgumentParser("Transfer Fitbit data to Google Fit")
	parser.add_argument("-d", "--debug", action="count", default=0, help="Increase debugging level")
	parser.add_argument("-g", "--google-creds", default="auth/google.json", help="Google credentials file")
	parser.add_argument("-f", "--fitbit-creds", default="auth/fitbit.json", help="Fitbit credentials file")
	args = parser.parse_args()

	# Init client objects and setup Google Fit data sources
	fitbitClient,fitbitCreds = GetFitbitClient(args.fitbit_creds)
	googleClient = GetGoogleClient(args.google_creds)
	dataSourceId = GetDataSourceId(GetDataSource(),args.google_creds)
	try:
		googleClient.users().dataSources().get(userId='me',dataSourceId=dataSourceId).execute()
	except HttpError as error:
		if not 'DataSourceId not found' in str(error):
			raise error
		# Data source doesn't already exist so, create it!
		googleClient.users().dataSources().create(userId='me',body=GetDataSource()).execute()

	# Testing
	print(googleClient.users().dataSources().list(userId='me').execute())
	print(fitbit_client.intraday_time_series('activities/steps'))

if __name__ == '__main__':
	main()

