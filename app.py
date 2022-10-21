#!/usr/bin/env python3
"""
Main class / entry point for the application 

__author__ = "Praveen Kumar Pendyala"
__email__ = "mail@pkp.io"
"""
import argparse
import logging
import dateutil.parser
import configparser
import json
from datetime import time

from helpers import Helper
from convertors import Convertor
from remote import DATE_FORMAT, Remote
from sys import exit

VERSION = "0.3"

def main():
	# Arguments parsing
	parser = argparse.ArgumentParser("All arguments are optional and read from config.ini when not passed.")
	parser.add_argument("-d", "--debug", action="count", default=0, help="Increase debugging level")
	parser.add_argument("-c", "--config", default='config.ini', help="Configuration file")
	parser.add_argument("-s", "--start-date", default="", help="Start date for sync in YYYY-MM-DD format")
	parser.add_argument("-e", "--end-date", default="", help="End data for sync in YYYY-MM-DD format")
	parser.add_argument("-g", "--google-creds", default="auth/google.json", help="Google credentials file")
	parser.add_argument("-f", "--fitbit-creds", default="auth/fitbit.json", help="Fitbit credentials file")
	parser.add_argument("-v", "--version", help="Fitbit-GoogleFit migration tool version", action="store_true")
	args = parser.parse_args()

	# Show version information if required
	if args.version:
		print('         fitbit-googlefit version {}'.format(VERSION))
		print('')

	# Reading configuration from config file
	config = configparser.ConfigParser()
	config.read(args.config)
	params = config['params']

	# Init objects
	helper = Helper(args.fitbit_creds, args.google_creds)
	weighTime = time.fromisoformat(params.get('weigh_time'))
	convertor = Convertor(args.google_creds, params.get('project_number'), None, weighTime)
	fitbitClient,googleClient = helper.GetFitbitClient(),helper.GetGoogleClient()
	remote = Remote(fitbitClient, googleClient, convertor, helper, None)

	# Get user's time zone info from Fitbit -- since Fitbit time stamps are not epoch and stored in user's timezone.
	userProfile = remote.ReadFromFitbit(fitbitClient.user_profile_get)
	tzinfo = dateutil.tz.gettz(userProfile['user']['timezone'])
	remote.UpdateTimezone(tzinfo)
	convertor.UpdateTimezone(tzinfo)

	# setup Google Fit data sources for each data type supported
	for dataType in ['steps', 'distance', 'weight', 'heart_rate', 'calories', 'activity', 'body_fat', 'sleep']:
		remote.CreateGoogleFitDataSource(dataType)

	# Decide the start and end dates of sync
	start_date_str = args.start_date if args.start_date != '' else params.get('start_date')
	end_date_str = args.end_date if args.end_date != '' else params.get('end_date')
	start_date = convertor.parseHumanReadableDate(start_date_str)
	end_date = convertor.parseHumanReadableDate(end_date_str)

	# Start syncing data for the given range
	for single_date in convertor.daterange(start_date, end_date):
		date_stamp = single_date.strftime(DATE_FORMAT)
		print('------------------------------   {}  -------------------------'.format(date_stamp))

		#----------------------------------     steps      ------------------------
		if params.getboolean('sync_steps'):
			remote.SyncFitbitToGoogleFit('steps',date_stamp)
		    
		#----------------------------------     distance   ------------------------
		if params.getboolean('sync_distance'):
			remote.SyncFitbitToGoogleFit('distance',date_stamp)
		    
		#----------------------------------     heart rate ------------------------
		if params.getboolean('sync_heartrate'):
			remote.SyncFitbitToGoogleFit('heart_rate',date_stamp)

		#----------------------------------     weight     ------------------------
		if params.getboolean('sync_weight'):
			remote.SyncFitbitToGoogleFit('weight',date_stamp)

		#----------------------------------     body fat   ------------------------
		if params.getboolean('sync_body_fat'):
			remote.SyncFitbitToGoogleFit('body_fat',date_stamp)

		#----------------------------------     calories   ------------------------
		if params.getboolean('sync_calories'):
			remote.SyncFitbitToGoogleFit('calories',date_stamp)

		#----------------------------------     sleep   ------------------------
		if params.getboolean('sync_sleep'):
			remote.SyncFitbitToGoogleFit('sleep',date_stamp)

		print('')

	#----------------------------------  activity logs  ------------------------
	if params.getboolean('sync_activities'):
		remote.SyncFitbitActivitiesToGoogleFit(start_date=start_date)

if __name__ == '__main__':
	try:
		print('')
		main()
		print('')
		print('--------------------------------------------------------------------------')
		print('                                     Like it ?                            ')
		print('star the repository : https://github.com/praveendath92/fitbit-googlefit')
		print('--------------------------------------------------------------------------')
		print('')
	except KeyboardInterrupt:
		print('')
		print('Stopping...')
		print('')
		exit(0)
