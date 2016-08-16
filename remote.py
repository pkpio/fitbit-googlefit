"""
Methods for remote api calls and synchronization from Fitbit to Google Fit

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

import convertors as convertor
import helpers as helper

FITBIT_API_URL = 'https://api.fitbit.com/1'

########################### Remote data read/write functions ############################

def ReadFromFitbit(api_call,*args,**kwargs):
	"""Peforms a read request from Fitbit API. The request will be paused if API rate limiting has 
	been reached!

	api_call -- api method to call
	args -- arguments to pass for the method
	"""
	# res_url,date_stamp,detail_level
	try:
	 	resp = api_call(*args,**kwargs)
	except HTTPTooManyRequests as e:
		print('-------------- Fitbit API rate limit reached ----------')
		print('Will retry in {} seconds. Time now is : {}'.format(e.retry_after_secs, str(datetime.datetime.now())))
		time.sleep(e.retry_after_secs)
		resp = ReadFromFitbit(api_call,*args,**kwargs)
	return resp

def WriteToGoogleFit(googleClient,dataSourceId,data_points):
	"""Write data to google fit

	googleClient -- authenticated google client
	dataSourceId -- data source id for google fit
	data_point -- google data points

	"""
	# max and min timestamps of any data point we will be adding to googlefit - required by gfit API.
	if len(data_points) == 0:
		return
	minLogNs = min([point['startTimeNanos'] for point in data_points])
	maxLogNs = max([point['endTimeNanos'] for point in data_points])
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

def WriteSessionToGoogleFit(googleClient,session_data):
	"""Write data to google fit

	googleClient -- authenticated google client
	session_data -- a session data
	"""
	googleClient.users().sessions().update(userId='me',sessionId=session_data['id'],body=session_data).execute()


########################################### Sync functions ########################################

def SyncFitbitToGoogleFit(fitbitClient,googleClient,dataType,date_stamp,tzinfo):
	"""
	Sync Fitbit data to Google fit for a given day.

	fitbitClient -- authenticated fitbit client
	googleClient -- authenticated googlefit client
	dataType -- fitbit data type to sync
	date_stamp -- timestamp in yyyy-mm-dd format of the day to sync
	tzinfo -- timezone info of Fitbit user
	"""
	if dataType in ('steps','distance','heart_rate'):
		return SyncFitbitIntradayToGoogleFit(fitbitClient, googleClient, dataType, date_stamp, tzinfo)
	elif dataType in ('weight','body_fat'):
		return SyncFitbitLogToGoogleFit(fitbitClient, googleClient, dataType, date_stamp, tzinfo)
	else:
		raise ValueError("Unexpected data type given!")

def SyncFitbitIntradayToGoogleFit(fitbitClient,googleClient,dataType,date_stamp,tzinfo):
	"""
	Sync Fitbit data of a particular intraday type to Google fit for a given day.

	fitbitClient -- authenticated fitbit client
	googleClient -- authenticated googlefit client
	dataType -- fitbit data type to sync
	date_stamp -- timestamp in yyyy-mm-dd format of the day to sync
	tzinfo -- timezone info of Fitbit user
	"""
	if dataType == 'steps':
		res_path,detail_level,resp_id  = 'activities/steps','1min','activities-steps-intraday'
	elif dataType == 'distance':
		res_path,detail_level,resp_id  = 'activities/distance','1min','activities-distance-intraday'
	elif dataType == 'heart_rate':
		res_path,detail_level,resp_id  = 'activities/heart','1sec','activities-heart-intraday'
	else:
		raise ValueError("Unexpected data type given!")
	dataSourceId = helper.GetDataSourceId(dataType)

	# Get intraday data from fitbit
	interday_raw = ReadFromFitbit(fitbitClient.intraday_time_series, res_path, base_date=date_stamp,
		detail_level=detail_level)
	intraday_data = interday_raw[resp_id]['dataset']

	# convert all fitbit data points to google fit data points
	googlePoints = [convertor.ConvertFibitPoint(date_stamp,data_point,dataType,tzinfo) for data_point in intraday_data]

	# Write a day of fitbit data to Google fit
	WriteToGoogleFit(googleClient, dataSourceId, googlePoints)
	print("Synced {} for day : {}".format(dataType,date_stamp))

def SyncFitbitLogToGoogleFit(fitbitClient,googleClient,dataType,date_stamp,tzinfo):
	"""
	Sync Fitbit logs of a particular type to Google Fit for a given day.

	fitbitClient -- authenticated fitbit client
	googleClient -- authenticated googlefit client
	dataType -- fitbit data type to sync
	date_stamp -- timestamp in yyyy-mm-dd format of the day to sync
	tzinfo -- timezone info of Fitbit user
	"""
	if dataType == 'weight':
		callMethod,resp_id = fitbitClient.get_bodyweight,'weight'
	elif dataType == 'body_fat':
		callMethod,resp_id = fitbitClient.get_bodyfat,'fat'
	else:
		raise ValueError("Unexpected data type given!")
	dataSourceId = helper.GetDataSourceId(dataType)

	# Get intraday distance for date_stamp from fitbit
	fitbitLogs = ReadFromFitbit(callMethod,base_date=date_stamp,end_date=date_stamp)[resp_id]

	# convert all fitbit data points to google fit data points
	googlePoints = [convertor.ConvertFibitPoint(date_stamp,data_point,dataType,tzinfo) for data_point in fitbitLogs]

	# Write a day of fitbit data to Google fit
	WriteToGoogleFit(googleClient, dataSourceId, googlePoints)
	print("Synced {} for day : {}".format(dataType,date_stamp))

def SyncFitbitActivitiesToGoogleFit(fitbitClient,googleClient,dataSourceId,start_date='',callurl=None):
	"""
	Sync activities data starting from a given day from Fitbit to Google fit.

	fitbitClient -- authenticated fitbit client
	googleClient -- authenticated googlefit client
	dataSourceId -- google fit data sourceid for activity segment
	start_date -- timestamp in yyyy-mm-dd format of the start day
	callurl -- url to fetch activities from
	"""
	# Fitbit activities list endpoint is in beta stage. It may break in the future and not directly supported
	# by the python client library.
	if not callurl:
		callurl = '{}/user/-/activities/list.json?afterDate={}&sort=asc&offset=0&limit=20'.format(FITBIT_API_URL,start_date)
	activities_raw = ReadFromFitbit(fitbitClient.make_request,callurl)
	activities = activities_raw['activities']

	for activity in activities:
		# 1. write a fit session about the activity 
		google_session = convertor.ConvertFitbitActivityLog(activity)
		WriteSessionToGoogleFit(googleClient, google_session)

		# 2. create activity segment data points for the activity
		activity_segment = dict(
			dataTypeName='com.google.activity.segment',
			startTimeNanos=convertor.nano(google_session['startTimeMillis']),
			endTimeNanos=convertor.nano(google_session['endTimeMillis']),
			value=[dict(intVal=google_session['activityType'])]
			)
		WriteToGoogleFit(googleClient, dataSourceId, [activity_segment])
	print("Synced {} activities between {} and {}".format(len(activities)),
		google_session['startTimeMillis'],google_session['endTimeMillis'])

	if activities_raw['pagination']['next'] != '':
	 	SyncFitbitActivitiesToGoogleFit(fitbitClient, googleClient,dataSourceId,
	 		callurl=activities_raw['pagination']['next'])

