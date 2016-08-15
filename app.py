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

########################### Unit conversion constants ###################
DATE_FORMAT = "%Y-%m-%d"
POUNDS_PER_KILOGRAM = 2.20462
METERS_PER_MILE = 1609.34

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

def UpdateFitbitCredentials(fitbitClient, filepath, credentials):
	"""Persists new fitbit credentials to local storage

	fitbitClient -- fitbit client object that contains the latest credentials
	filepath -- path to file containing oauth credentials in json format
	credentails -- previous credentials object
	"""
	dump = False
	for t in ('access_token', 'refresh_token'):
		if fitbitClient.client.token[t] != credentials[t]:
			credentials[t] = fitbitClient.client.token[t]
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
	elif type == 'distance':
		dataType=dict(name='com.google.distance.delta',field=[dict(name='distance',format='floatPoint')])
	elif type == 'weight':
		dataType=dict(name='com.google.weight',field=[dict(name='weight',format='floatPoint')])
	elif type == 'heart_rate':
		dataType=dict(name='com.google.heart_rate.bpm',field=[dict(name='bpm',format='floatPoint')])
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



########################### Type convertor functions ############################

dawnOfTime = datetime.datetime(1970, 1, 1, tzinfo=dateutil.tz.tzutc())

def EpochOfFitbitTimestamp(timestamp, tzinfo=None):
	"""Returns a epoch time stamp (in milliseconds). Useful for converting fitbit timestamps to epoch values.

	timestamp -- date-time stamp as a string "yyyy-mm-dd hh:mm:ss" (24-hour) or any other standard format
	tzinfo -- timezone of the fitbit user (optional if this is included in the timestamp string)
	"""
	if tzinfo:
		logTime = dateutil.parser.parse(timestamp).replace(tzinfo=tzinfo)
	else:
		logTime = dateutil.parser.parse(timestamp)
	return int((logTime - dawnOfTime).total_seconds() * 1000)

def nano(val):
	"""Converts epoch milliseconds to nano seconds precision"""
	return int(val * (10**6))

def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)

def ConvertFibitStepsPoint(date, data_point, tzinfo):
	"""Converts a single Fitbit intraday steps data point to Google fit data point

	date -- date to which the data_point belongs to in "yyyy-mm-dd" format
	data_point -- a single Fitbit intraday step data point
	tzinfo --  time zone information of the user
	"""
	timestamp = "{} {}".format(date, data_point['time'])
	epoch_time_nanos = nano(EpochOfFitbitTimestamp(timestamp, tzinfo))

	return dict(
		dataTypeName='com.google.step_count.delta',
		startTimeNanos=epoch_time_nanos,
		endTimeNanos=epoch_time_nanos+110,
		value=[dict(intVal=data_point['value'])]
		)

def ConvertFibitDistancePoint(date, data_point, tzinfo):
	"""Converts a single Fitbit intraday distance data point to Google fit data point

	date -- date to which the data_point belongs to in "yyyy-mm-dd" format
	data_point -- a single Fitbit intraday step data point
	tzinfo --  time zone information of the user
	"""
	timestamp = "{} {}".format(date, data_point['time'])
	epoch_time_nanos = nano(EpochOfFitbitTimestamp(timestamp, tzinfo))
	gfit_distance = data_point['value'] * METERS_PER_MILE

	return dict(
		dataTypeName='com.google.distance.delta',
		startTimeNanos=epoch_time_nanos,
		endTimeNanos=epoch_time_nanos+110,
		value=[dict(fpVal=gfit_distance)]
		)

def ConvertFibitHRPoint(date, data_point, tzinfo):
	"""Converts a single Fitbit intraday heart rate data point to Google fit data point

	date -- date to which the data_point belongs to in "yyyy-mm-dd" format
	data_point -- a single Fitbit intraday step data point
	tzinfo --  time zone information of the user
	"""
	timestamp = "{} {}".format(date, data_point['time'])
	epoch_time_nanos = nano(EpochOfFitbitTimestamp(timestamp, tzinfo))

	return dict(
		dataTypeName='com.google.heart_rate.bpm',
		startTimeNanos=epoch_time_nanos,
		endTimeNanos=epoch_time_nanos+110,
		value=[dict(fpVal=data_point['value'])]
		)



########################### Remote data read/write functions ############################

def ReadFromFitbitIntraday(fitbitClient,res_url,date_stamp,detail_level):
	"""Peforms an intraday read request from Fitbit API. The request will be paused if API rate limiting has 
	been reached!
	"""
	try:
	 	resp = fitbitClient.intraday_time_series(res_url,base_date=date_stamp,detail_level=detail_level)
	except HTTPTooManyRequests as e:
		print('-------------- Fitbit API rate limit reached ----------')
		print('Will retry in {} seconds. Time now is : {}'.format(e.retry_after_secs, str(datetime.datetime.now())))
		time.sleep(e.retry_after_secs)
		resp = ReadFromFitbitIntraday(fitbitClient, res_url, date_stamp, detail_level)
	return resp

def WriteToGoogleFit(googleClient,dataSourceId,date_stamp,tzinfo,data_points):
	"""Write data to google fit

	googleClient -- authenticated google client
	dataSourceId -- data source id for google fit
	date_stamp -- fitbit timestamp of the day to which the data corresponds to
	tzinfo -- time zone info of the fitbit user
	data_point -- google data points

	"""
	# max and min timestamps of any data point we will be adding to googlefit - required by gfit API.
	# we generate datasetId from these so, multiple syncs over same day won't export duplicates - happy coincidence!
	minLogNs = nano(EpochOfFitbitTimestamp("{} 00:00:00".format(date_stamp),tzinfo))
	maxLogNs = nano(EpochOfFitbitTimestamp("{} 23:59:59".format(date_stamp),tzinfo))
	datasetId = '%s-%s' % (minLogNs, maxLogNs)

	googleClient.users().dataSources().datasets().patch(
			userId='me',
			dataSourceId=dataSourceId,
			datasetId=datasetId,
			body=dict(
				dataSourceId=dataSourceId,
				maxEndTimeNs=maxLogNs,
				minStartTimeNs=minLogNs,
				point=data_points)
	).execute()


def SyncFitbitStepsToGoogleFit(fitbitClient,googleClient,date_stamp,tzinfo,dataSourceId):
	"""
	Sync Fitbit intraday steps for a particular day to Google fit.

	fitbitClient -- authenticated fitbit client
	googleClient -- authenticated googlefit client
	date_stamp -- timestamp in yyyy-mm-dd format of the day to sync
	tzinfo -- timezone info of the user in which the steps are recorded
	dataSourceId -- google fit data sourceid for steps
	"""
	# Get intraday steps for date_stamp from fitbit
	interday_raw = ReadFromFitbitIntraday(fitbitClient, 'activities/steps', date_stamp, '1min')
	steps_data = interday_raw['activities-steps-intraday']['dataset']

	# convert all fitbit data points to google fit data points
	googleStepPoints = [ConvertFibitStepsPoint(date_stamp, data_point, tzinfo) for data_point in steps_data]

	# Write a day of fitbit data to Google fit
	WriteToGoogleFit(googleClient, dataSourceId, date_stamp, tzinfo, googleStepPoints)
	print("Synced steps for day : {}".format(date_stamp))

def SyncFitbitDistanceToGoogleFit(fitbitClient,googleClient,date_stamp,tzinfo,dataSourceId):
	"""
	Sync Fitbit intraday distance for a particular day to Google fit.

	fitbitClient -- authenticated fitbit client
	googleClient -- authenticated googlefit client
	date_stamp -- timestamp in yyyy-mm-dd format of the day to sync
	tzinfo -- timezone info of the user in which the steps are recorded
	dataSourceId -- google fit data sourceid for distance
	"""
	# Get intraday distance for date_stamp from fitbit
	interday_raw = ReadFromFitbitIntraday(fitbitClient, 'activities/distance', date_stamp, '1min')
	distances_data = interday_raw['activities-distance-intraday']['dataset']

	# convert all fitbit data points to google fit data points
	googleDistancePoints = [ConvertFibitDistancePoint(date_stamp, data_point, tzinfo) for data_point in distances_data]

	# Write a day of fitbit data to Google fit
	WriteToGoogleFit(googleClient, dataSourceId, date_stamp, tzinfo, googleDistancePoints)
	print("Synced distance for day : {}".format(date_stamp))

def SyncFitbitHRToGoogleFit(fitbitClient,googleClient,date_stamp,tzinfo,dataSourceId):
	"""
	Sync Fitbit intraday heart rate for a particular day to Google fit.

	fitbitClient -- authenticated fitbit client
	googleClient -- authenticated googlefit client
	date_stamp -- timestamp in yyyy-mm-dd format of the day to sync
	tzinfo -- timezone info of the user in which the steps are recorded
	dataSourceId -- google fit data sourceid for heart rate
	"""
	# Get intraday distance for date_stamp from fitbit
	interday_raw = ReadFromFitbitIntraday(fitbitClient, 'activities/heart', date_stamp, '1sec')
	hr_data = interday_raw['activities-heart-intraday']['dataset']

	# convert all fitbit data points to google fit data points
	googleHRPoints = [ConvertFibitHRPoint(date_stamp, data_point, tzinfo) for data_point in hr_data]

	# Write a day of fitbit data to Google fit
	WriteToGoogleFit(googleClient, dataSourceId, date_stamp, tzinfo, googleHRPoints)
	print("Synced heart rate for day : {}".format(date_stamp))



#======================== Main application code =========================

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
	fitbitClient,fitbitCreds = GetFitbitClient(args.fitbit_creds)
	googleClient = GetGoogleClient(args.google_creds)
	for dataType in ['steps', 'distance', 'weight', 'heart_rate']:
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
	dataSourceIdDistance = GetDataSourceId(GetDataSource('distance'),args.google_creds)
	dataSourceIdWeight = GetDataSourceId(GetDataSource('weight'),args.google_creds)
	dataSourceIdHR = GetDataSourceId(GetDataSource('heart_rate'),args.google_creds)

	# Testing
	# logTime = dateutil.parser.parse('2016-08-15T11:14:15.000+02:00')
	# print((logTime - dawnOfTime).total_seconds())
	# exit()
	# activities = fitbitClient.make_request(
	# 	'https://api.fitbit.com/1/user/-/activities/list.json?afterDate=2016-08-15&sort=asc&offset=0&limit=10')['activities']
	# for activity in activities:
	# 	act_name = activity['activityName']
	# 	if act_name == 'Run':
	# 		startTimeMillis = 1471252440000
	# 		# unix_time_seconds(time.strptime(activity['startTime'], '%Y-%m-%dT%H:%M:%S.%f+02:00').datetime())*1000-2*60*60*1000
	# 		endTimeMillis = startTimeMillis + activity['duration'] + 100*1000

	# 		print(googleClient.users().sessions().update(
	# 			userId='me',
	# 			sessionId='io.pkp.fbit-gfit:fitbit:{}'.format(activity['logId']),
	# 			body=dict(
	# 				modifiedTimeMillis=str(int(round(time.time() * 1000))),
	# 				endTimeMillis=str(endTimeMillis),
	# 				description='A Fitbit activity of type - {}'.format(activity['logType']),
	# 				activityType=8,
	# 				application=dict(
	# 					name='Fbit-Gfit',
	# 					detailsUrl=''
	# 					),
	# 				startTimeMillis=str(startTimeMillis),
	# 				activeTimeMillis=activity['duration'] + 100*1000,
	# 				id='io.pkp.fbit-gfit:fitbit:{}'.format(activity['logId']),
	# 				name=activity['activityName'])
	# 			).execute())
	# 		exit()

	# Get user's time zone info from Fitbit -- since Fitbit time stamps are not epoch and stored user's timezone.
	userProfile = fitbitClient.user_profile_get()
	tzinfo = dateutil.tz.gettz(userProfile['user']['timezone'])

	# Start fetching date for a given range of days
	start_date = datetime.datetime.strptime(params.get('start_date'), DATE_FORMAT).date()
	end_date = datetime.datetime.strptime(params.get('end_date'), DATE_FORMAT).date()

	for single_date in daterange(start_date, end_date):
		date_stamp = single_date.strftime(DATE_FORMAT)

		#---------------------------------- 	steps 		 ------------------------
		if params.getboolean('sync_steps'):
			SyncFitbitStepsToGoogleFit(fitbitClient,googleClient,date_stamp,tzinfo,dataSourceIdSteps)
		    
		#---------------------------------- 	distance 		 ------------------------
		if params.getboolean('sync_distance'):
			SyncFitbitDistanceToGoogleFit(fitbitClient,googleClient,date_stamp,tzinfo,dataSourceIdDistance)
		    
		#---------------------------------- 	heart rate 		 ------------------------
		if params.getboolean('sync_heartrate'):
			SyncFitbitHRToGoogleFit(fitbitClient,googleClient,date_stamp,tzinfo,dataSourceIdHR)

if __name__ == '__main__':
	main()

