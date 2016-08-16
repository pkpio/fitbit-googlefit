#!/usr/bin/env python
"""
Main class / entry point for the application 

__author__ = "Praveen Kumar Pendyala"
__email__ = "mail@pkp.io"
"""
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
from datetime import timedelta, date

import fitbit
from fitbit.exceptions import HTTPTooManyRequests
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2Credentials
from googleapiclient.errors import HttpError

import helpers as helper
import convertors as convertor
import remote as remote

DATE_FORMAT = "%Y-%m-%d"

def main():
	# Arguments parsing
	parser = argparse.ArgumentParser("All arguments are optional and read from config.ini when not passed.")
	parser.add_argument("-d", "--debug", action="count", default=0, help="Increase debugging level")
	parser.add_argument("-s", "--start-date", default="", help="Start date for sync in YYYY-MM-DD format")
	parser.add_argument("-e", "--end-date", default="", help="End data for sync in YYYY-MM-DD format")
	parser.add_argument("-g", "--google-creds", default="auth/google.json", help="Google credentials file. Obtain using auth/auth_google.py")
	parser.add_argument("-f", "--fitbit-creds", default="auth/fitbit.json", help="Fitbit credentials file. Obtain using auth/auth_fitbit.py")
	args = parser.parse_args()

	# Reading configuration from config file
	config = configparser.ConfigParser()
	config.read('config.ini')
	params = config['params']

	# Init client objects
	fitbitClient,fitbitCreds = helper.GetFitbitClient(args.fitbit_creds)
	googleClient = helper.GetGoogleClient(args.google_creds)

	# Save creds file path to helper class - saves some arguments in future calls
	helper.SetCredsFilePaths(args.fitbit_creds,args.google_creds)

	# setup Google Fit data sources for each data type supported
	for dataType in ['steps', 'distance', 'weight', 'body_fat', 'heart_rate', 'calories', 'activity']:
		dataSourceId = helper.GetDataSourceId(dataType)
		try:
			googleClient.users().dataSources().get(userId='me',dataSourceId=dataSourceId).execute()
		except HttpError as error:
			if not 'DataSourceId not found' in str(error):
				raise error
			# Data source doesn't already exist so, create it!
			googleClient.users().dataSources().create(userId='me',body=helper.GetDataSource(dataType)).execute()

	# Get user's time zone info from Fitbit -- since Fitbit time stamps are not epoch and stored user's timezone.
	userProfile = remote.ReadFromFitbit(fitbitClient.user_profile_get)
	tzinfo = dateutil.tz.gettz(userProfile['user']['timezone'])

	# Start fetching date for a given range of days
	start_date_str = args.start_date if args.start_date != '' else params.get('start_date')
	end_date_str = args.end_date if args.end_date != '' else params.get('end_date')
	start_date = datetime.datetime.strptime(start_date_str, DATE_FORMAT).date()
	end_date = datetime.datetime.strptime(end_date_str, DATE_FORMAT).date()

	try:
		for single_date in convertor.daterange(start_date, end_date):
			date_stamp = single_date.strftime(DATE_FORMAT)
			print('------------------------------   {}  -------------------------'.format(date_stamp))

			#----------------------------------     steps      ------------------------
			if params.getboolean('sync_steps'):
				remote.SyncFitbitToGoogleFit(fitbitClient,googleClient,'steps',date_stamp,tzinfo)
			    
			#----------------------------------     distance   ------------------------
			if params.getboolean('sync_distance'):
				remote.SyncFitbitToGoogleFit(fitbitClient,googleClient,'distance',date_stamp,tzinfo)
			    
			#----------------------------------     heart rate ------------------------
			if params.getboolean('sync_heartrate'):
				remote.SyncFitbitToGoogleFit(fitbitClient,googleClient,'heart_rate',date_stamp,tzinfo)

			#----------------------------------     weight     ------------------------
			if params.getboolean('sync_weight'):
				remote.SyncFitbitToGoogleFit(fitbitClient,googleClient,'weight',date_stamp,tzinfo)

			#----------------------------------     body fat   ------------------------
			if params.getboolean('sync_body_fat'):
				remote.SyncFitbitToGoogleFit(fitbitClient,googleClient,'body_fat',date_stamp,tzinfo)

			#----------------------------------     calories   ------------------------
			if params.getboolean('sync_calories'):
				remote.SyncFitbitToGoogleFit(fitbitClient,googleClient,'calories',date_stamp,tzinfo)

			print('')

		#----------------------------------  activity logs  ------------------------
		if params.getboolean('sync_activities'):
			remote.SyncFitbitActivitiesToGoogleFit(fitbitClient,googleClient,helper.GetDataSourceId('activity'),
				start_date=start_date)

	finally:
		# Persist the latest fitbit access tokens for future use
		helper.UpdateFitbitCredentials(fitbitClient,fitbitCreds)


if __name__ == '__main__':
	main()

