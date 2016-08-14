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

def GetDataSource(type='steps'):
	"""Returns a data source for Google Fit data logging
	
	type - type of data. Possible options: steps, weight, heart_rate
	"""
	if type == 'steps':
		dataType=dict(name='com.google.step_count.delta',field=[dict(name='steps',format='integer')])
	elif type == 'weight':
		dataType=dict(name='com.google.weight',field=[dict(format='floatPoint', name='weight')])
	elif type == 'heart_rate':
		dataType=dict(name='com.google.heart_rate.bpm',field=[dict(format='floatPoint', name='bpm')])
	else:
		raise ValueError("Unexpected data type given!")

	return dict(
		type='raw',
		application=dict(name='fbit-gfit'),
		dataType=dataType,
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

dawnOfTime = datetime.datetime(1970, 1, 1, tzinfo=dateutil.tz.tzutc())

def epochOfFitbitLog(date, dataPoint, tzinfo):
	logTimestamp = "{} {}".format(date, dataPoint['time'])
	logTime = dateutil.parser.parse(logTimestamp).replace(tzinfo=tzinfo)
	return (logTime - dawnOfTime).total_seconds()

def nano(val):
	"""Converts a number to nano (str)."""
	return '%d' % (val * 1e9)

def FitbitStepsToGoogleSteps(date, steps_point, tzinfo):
	logSecs = epochOfFitbitLog(date, steps_point, tzinfo)

	return dict(
		dataTypeName='com.google.step_count.delta',
		endTimeNanos=int(nano(logSecs))+110,
		startTimeNanos=nano(logSecs),
		value=[dict(intVal=steps_point['value'])]
		)
def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)


#======================== Main application code =========================
def main():
	# Arguments parsing
	parser = argparse.ArgumentParser("Transfer Fitbit data to Google Fit")
	parser.add_argument("-d", "--debug", action="count", default=0, help="Increase debugging level")
	parser.add_argument("-g", "--google-creds", default="auth/google.json", help="Google credentials file")
	parser.add_argument("-f", "--fitbit-creds", default="auth/fitbit.json", help="Fitbit credentials file")
	args = parser.parse_args()

	# Init client objects and setup Google Fit data sources for each type
	fitbitClient,fitbitCreds = GetFitbitClient(args.fitbit_creds)
	googleClient = GetGoogleClient(args.google_creds)
	for dataType in ['steps', 'weight', 'heart_rate']:
		dataSource = GetDataSource(dataType)
		dataSourceId = GetDataSourceId(dataSource,args.google_creds)
		try:
			googleClient.users().dataSources().get(userId='me',dataSourceId=dataSourceId).execute()
		except HttpError as error:
			if not 'DataSourceId not found' in str(error):
				raise error
			# Data source doesn't already exist so, create it!
			googleClient.users().dataSources().create(userId='me',body=dataSource).execute()
	dataSourceIdSteps = GetDataSourceId(GetDataSource('steps'),args.google_creds)
	dataSourceIdWeight = GetDataSourceId(GetDataSource('weight'),args.google_creds)
	dataSourceIdHR = GetDataSourceId(GetDataSource('heart_rate'),args.google_creds)

	# Get user's time zone info from Fitbit -- since Fitbit time stamps are not epoch
	userProfile = fitbitClient.user_profile_get()
	tzinfo = dateutil.tz.gettz(userProfile['user']['timezone'])

	# Iterate over a range of dates
	start_date = date(2015, 5, 17)
	end_date = date(2016, 8, 14)

	for single_date in daterange(start_date, end_date):
		day_stamp = single_date.strftime("%Y-%m-%d")

	    # Start getting data from fitbit
		interday_raw = fitbitClient.intraday_time_series('activities/steps',base_date=day_stamp,detail_level='1min')
		steps_day = interday_raw['activities-steps'][0]['dateTime']
		steps_data = interday_raw['activities-steps-intraday']['dataset']

		# Probably not required - we do it on daily basis!
		steps_data_times = [epochOfFitbitLog(steps_day, log, tzinfo) for log in steps_data]
		minLogNs = nano(min(steps_data_times))
		maxLogNs = int(nano(max(steps_data_times)))+200


		googleStepPoints = [FitbitStepsToGoogleSteps(steps_day, log, tzinfo) for log in steps_data]
		datasetId = '%s-%s' % (minLogNs, maxLogNs)

		# Write a day of fitbit data
		"""
		print(googleClient.users().dataSources().datasets().get(
		userId='me',
		datasetId=datasetId,
		dataSourceId=dataSourceIdSteps
		).execute())
		"""
		googleClient.users().dataSources().datasets().patch(
				userId='me',
				dataSourceId=dataSourceIdSteps,
				datasetId=datasetId,
				body=dict(
					dataSourceId=dataSourceIdSteps,
					maxEndTimeNs=maxLogNs,
					minStartTimeNs=minLogNs,
					point=googleStepPoints)
		).execute()
		print("Synced for day : %s"%(steps_day))

if __name__ == '__main__':
	main()

