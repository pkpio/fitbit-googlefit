#!/usr/bin/env python3
"""
Main class / entry point for the application

__author__ = "Praveen Kumar Pendyala"
__email__ = "mail@pkp.io"
"""
import time,argparse,logging,datetime,dateutil.parser,configparser,json,os
from datetime import timedelta, date
from helpers import *
from convertors import *
from remote import *
from sys import exit
from shutil import copyfile,which
from time import sleep
from pathlib import Path
from auth import auth_fitbit,auth_google

VERSION = "0.3"
DATE_FORMAT = "%Y-%m-%d"

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

	#copy the config file from template and edit it
	try:
	    config = Path("./config.ini")
	    configTemplate = Path("./config.template.ini")
	    # check if config.ini already exists
	    if config.is_file() == False:
	        # if config.ini doesn't exist, copy it from the template
	        copyfile(str(configTemplate), str(config))

	        #check for $EDITOR, or else use first standard editor
	        if os.environ.get("EDITOR"):
	            print("Found $EDITOR")
	            editor = which(os.environ.get("EDITOR"))
	        elif which("nano"):
	            print("Running nano")
	            editor = which("nano")
	        elif which("vim"):
	            print("Running VIM")
	            editor = which("vim")
	        elif which("vi"):
	            print("Running VI")
	            editor = which("vi")
	        else:
	            #no editors found, copy template as is and give them a chance to quit the app to change the config themselves
	            print("\n======================================================================")
	            print("using default config")
	            print("press Ctrl+c if you wish to edit config.ini with your own editor first")
	            print("======================================================================\n")
	            sleep(5)
	        if editor:
	            print("\n======================================================================")
	            print("Customize the config file...")
	            print("======================================================================\n")
	            sleep(2)
	            os.system(editor + " " + str(config))
	except KeyError:
	    pass

	fitbitauthfile = Path("./auth/fitbit.json")
	googleauthfile = Path("./auth/google.json")
	# if auth/fitbit.json doesn't exist
	if fitbitauthfile.is_file() == False:
		#send to fitbit's site for authentication
		print("""\n===========================================================================\n===========================================================================\n\nGo to this site and register a new Fitbit app\n https://dev.fitbit.com/apps/new \n\n\nApplication Name :              --Choose a name--\nDescription :                   --Choose a description--\nApplication Website :           --Your website--\nOrganization :                  --Choose an organization--\nOrganization Website :          --Your website--\nOAuth 2.0 Application Type :    **Must choose 'Personal'**\nCallback URL :                  http://localhost:8080/ \nDefault Access Type :           Read-Only\n\nNote :\n1. Use your own information for fields marked --\n2. Make sure you copy the Callback URL exactly (including the last /)\n3. Application Type MUST be Personal\n\nMake a note of your 'OAuth 2.0 Client ID' and 'Client Secret'\n===========================================================================\n===========================================================================\n""")
		sleep(2)
		# prompt if on headless or browser
		isbrowser = helpers.get_bool("Does this system have a native display and a browser?")
		fitbitclientid = input("What's your Fitbit Client ID? ")
		fitbitclientsecret = input("What's your Fitbit Client Secret? ")
		# run auth/auth_fitbit.py
		if isbrowser == True:
			auth_fitbit.main("-i " + fitbitclientid + " -s " + fitbitclientsecret)
		else
			auth_fitbit.main("-i " + fitbitclientid + " -s " + fitbitclientsecret + " --console")
	# if auth/google.json doesn't exist
	if googleauthfile.is_file() == False:
		print("""\n\n===========================================================================\n===========================================================================\n\nGo to https://console.developers.google.com/flows/enableapi?apiid=fitness\n\n1. Click 'Continue'. Then select 'Go to credentials' and select 'Client ID'.\n2. Under 'Application type', select 'Other' and hit 'Create'.\n3. Make a note of 'Client ID' and 'Client Secret'\n\n===========================================================================\n===========================================================================\n""")
		sleep(2)
		# check if already asked for headless or browser
		try:
			isbrowser
		except NameError:
			isbrowser = helpers.get_bool("Does this system have a native display and a browser?")
		googleclientid = input("What's your Google Client ID? ")
		googleclientsecret = input("What's your Google Client Secret? ")
		# run auth/auth_google.py
		if isbrowser == True:
			auth_google.main("-i " + googleclientid + " -s " + googleclientsecret)
		else
			auth_google.main("-i " + googleclientid + " -s " + googleclientsecret + " --console")


	# Reading configuration from config file
	config = configparser.ConfigParser()
	config.read(args.config)
	params = config['params']

	# Init objects
	helper = Helper(args.fitbit_creds, args.google_creds)
	convertor = Convertor(args.google_creds, None)
	fitbitClient,googleClient = helper.GetFitbitClient(),helper.GetGoogleClient()
	remote = Remote(fitbitClient, googleClient, convertor, helper)

	# Get user's time zone info from Fitbit -- since Fitbit time stamps are not epoch and stored in user's timezone.
	userProfile = remote.ReadFromFitbit(fitbitClient.user_profile_get)
	tzinfo = dateutil.tz.gettz(userProfile['user']['timezone'])
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
	except KeyError:
	    pass
	except KeyboardInterrupt:
		print('')
		print('Stopping...')
		print('')
		exit(0)
