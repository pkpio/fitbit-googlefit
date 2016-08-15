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
	parser = argparse.ArgumentParser("Transfer Fitbit data to Google Fit")
	parser.add_argument("-d", "--debug", action="count", default=0, help="Increase debugging level")
	parser.add_argument("-g", "--google-creds", default="auth/google.json", help="Google credentials file")
	parser.add_argument("-f", "--fitbit-creds", default="auth/fitbit.json", help="Fitbit credentials file")
	args = parser.parse_args()

	# Reading configuration from config file
	config = configparser.ConfigParser()
	config.read('config.ini')
	params = config['params']

	# Init client objects and setup Google Fit data sources for each type
	fitbitClient,fitbitCreds = helper.GetFitbitClient(args.fitbit_creds)
	googleClient = helper.GetGoogleClient(args.google_creds)
	helper.SetGoogleCredsFilePath(args.google_creds)
	for dataType in ['steps', 'distance', 'weight', 'heart_rate']:
		dataSourceId = helper.GetDataSourceId(dataType,args.google_creds)
		try:
			googleClient.users().dataSources().get(userId='me',dataSourceId=dataSourceId).execute()
		except HttpError as error:
			if not 'DataSourceId not found' in str(error):
				raise error
			# Data source doesn't already exist so, create it!
			googleClient.users().dataSources().create(userId='me',body=dataSource).execute()

	# Get user's time zone info from Fitbit -- since Fitbit time stamps are not epoch and stored user's timezone.
	userProfile = remote.ReadFromFitbit(fitbitClient.user_profile_get)
	tzinfo = dateutil.tz.gettz(userProfile['user']['timezone'])

	# Start fetching date for a given range of days
	start_date = datetime.datetime.strptime(params.get('start_date'), DATE_FORMAT).date()
	end_date = datetime.datetime.strptime(params.get('end_date'), DATE_FORMAT).date()
	for single_date in convertor.daterange(start_date, end_date):
		date_stamp = single_date.strftime(DATE_FORMAT)

		#---------------------------------- 	steps 		 ------------------------
		if params.getboolean('sync_steps'):
			remote.SyncFitbitStepsToGoogleFit(fitbitClient,googleClient,date_stamp,tzinfo,helper.GetDataSourceId('steps'))
		    
		#---------------------------------- 	distance 		 ------------------------
		if params.getboolean('sync_distance'):
			remote.SyncFitbitDistanceToGoogleFit(fitbitClient,googleClient,date_stamp,tzinfo,helper.GetDataSourceId('distance'))
		    
		#---------------------------------- 	heart rate 		 ------------------------
		if params.getboolean('sync_heartrate'):
			remote.SyncFitbitHRToGoogleFit(fitbitClient,googleClient,date_stamp,tzinfo,helper.GetDataSourceId('heart_rate'))

		#---------------------------------- 	weight 		 ------------------------
		if params.getboolean('sync_weight'):
			remote.SyncFitbitWeightToGoogleFit(fitbitClient,googleClient,date_stamp,tzinfo,helper.GetDataSourceId('weight'))


if __name__ == '__main__':
	main()

