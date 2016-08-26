#!/usr/bin/env python3
"""
__author__ = "Praveen Kumar Pendyala"
__email__ = "mail@pkp.io"
"""
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

class Remote:
	"""Methods for remote api calls and synchronization from Fitbit to Google Fit"""
	
	FITBIT_API_URL = 'https://api.fitbit.com/1'
	GFIT_MAX_POINTS_PER_UPDATE = 2000 # Max number of data points that can be sent in a single update request

	def __init__(self, fitbitClient, googleClient, convertor, helper):
		""" Intialize a remote object.
		
		fitbitClient -- authenticated fitbit client
		googleClient -- authenticated google client
		convertor -- a convertor object for type conversions
		helper -- a helper object for fitbit credentials update
		"""
		self.fitbitClient = fitbitClient
		self.googleClient = googleClient
		self.convertor = convertor
		self.helper = helper

	########################### Remote data read/write methods ############################

	def ReadFromFitbit(self, api_call, *args, **kwargs):
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
			print('Will retry in {} seconds. Time now is : {}'.format(
				e.retry_after_secs, 
				str(datetime.datetime.now())
				))
			time.sleep(e.retry_after_secs)
			resp = self.ReadFromFitbit(api_call,*args,**kwargs)
		return resp

	def WriteToGoogleFit(self, dataSourceId, data_points):
		"""Write data to google fit

		dataSourceId -- data source id for google fit
		data_point -- google data points
		"""
		# max and min timestamps of any data point we will be adding to googlefit - required by gfit API.
		if len(data_points) == 0:
			return
		minLogNs = min([point['startTimeNanos'] for point in data_points])
		maxLogNs = max([point['endTimeNanos'] for point in data_points])
		datasetId = '%s-%s' % (minLogNs, maxLogNs)

		if len(data_points) < self.GFIT_MAX_POINTS_PER_UPDATE:
			self.googleClient.users().dataSources().datasets().patch(
					userId='me',
					dataSourceId=dataSourceId,
					datasetId=datasetId,
					body=dict(
						dataSourceId=dataSourceId,
						maxEndTimeNs=maxLogNs,
						minStartTimeNs=minLogNs,
						point=data_points)
			).execute()
		else:
			half = int(len(data_points)/2)
			self.WriteToGoogleFit(dataSourceId, data_points[:half])
			self.WriteToGoogleFit(dataSourceId, data_points[half:])

	def WriteSessionToGoogleFit(self, session_data):
		"""Write data to google fit

		session_data -- a session data
		"""
		self.googleClient.users().sessions().update(
			userId='me',
			sessionId=session_data['id'],
			body=session_data).execute()


	def CreateGoogleFitDataSource(self, dataType):
		try:
			self.googleClient.users().dataSources().get(
				userId='me',
				dataSourceId=self.convertor.GetDataSourceId(dataType)).execute()
		except HttpError as error:
			if not 'DataSourceId not found' in str(error):
				raise error
			# Data source doesn't already exist so, create it!
			self.googleClient.users().dataSources().create(
				userId='me',
				body=self.convertor.GetDataSource(dataType)).execute()


	########################################### Sync methods ########################################

	def SyncFitbitToGoogleFit(self, dataType, date_stamp):
		"""
		Sync Fitbit data to Google fit for a given day.

		dataType -- fitbit data type to sync
		date_stamp -- timestamp in yyyy-mm-dd format of the day to sync
		"""
		# Persist current credentials. Incase the request fails.
		self.helper.UpdateFitbitCredentials(self.fitbitClient)

		if dataType in ('steps','distance','heart_rate','calories'):
			return self.SyncFitbitIntradayToGoogleFit(dataType, date_stamp)
		elif dataType in ('weight','body_fat'):
			return self.SyncFitbitLogToGoogleFit(dataType, date_stamp)
		else:
			raise ValueError("Unexpected data type given!")

	def SyncFitbitIntradayToGoogleFit(self, dataType, date_stamp):
		"""
		Sync Fitbit data of a particular intraday type to Google fit for a given day.

		dataType -- fitbit data type to sync
		date_stamp -- timestamp in yyyy-mm-dd format of the day to sync
		"""
		if dataType == 'steps':
			res_path,detail_level,resp_id  = 'activities/steps','1min','activities-steps-intraday'
		elif dataType == 'distance':
			res_path,detail_level,resp_id  = 'activities/distance','1min','activities-distance-intraday'
		elif dataType == 'heart_rate':
			res_path,detail_level,resp_id  = 'activities/heart','1sec','activities-heart-intraday'
		elif dataType == 'calories':
			res_path,detail_level,resp_id  = 'activities/calories','1min','activities-calories-intraday'
		else:
			raise ValueError("Unexpected data type given!")
		dataSourceId = self.convertor.GetDataSourceId(dataType)

		# Get intraday data from fitbit
		interday_raw = self.ReadFromFitbit(self.fitbitClient.intraday_time_series, res_path, base_date=date_stamp,
			detail_level=detail_level)
		intraday_data = interday_raw[resp_id]['dataset']

		# convert all fitbit data points to google fit data points
		googlePoints = [self.convertor.ConvertFibitPoint(date_stamp,point,dataType) for point in intraday_data]

		# Write a day of fitbit data to Google fit
		self.WriteToGoogleFit(dataSourceId, googlePoints)
		print("synced {}".format(dataType))

	def SyncFitbitLogToGoogleFit(self, dataType, date_stamp):
		"""
		Sync Fitbit logs of a particular type to Google Fit for a given day.

		dataType -- fitbit data type to sync
		date_stamp -- timestamp in yyyy-mm-dd format of the day to sync
		"""
		if dataType == 'weight':
			callMethod,resp_id = self.fitbitClient.get_bodyweight,'weight'
		elif dataType == 'body_fat':
			callMethod,resp_id = self.fitbitClient.get_bodyfat,'fat'
		else:
			raise ValueError("Unexpected data type given!")
		dataSourceId = self.convertor.GetDataSourceId(dataType)

		# Get intraday distance for date_stamp from fitbit
		fitbitLogs = self.ReadFromFitbit(callMethod,base_date=date_stamp,end_date=date_stamp)[resp_id]

		# convert all fitbit data points to google fit data points
		googlePoints = [self.convertor.ConvertFibitPoint(date_stamp,point,dataType) for point in fitbitLogs]

		# Write a day of fitbit data to Google fit
		self.WriteToGoogleFit(dataSourceId, googlePoints)
		print("synced {}".format(dataType))

	def SyncFitbitSleepToGoogleFit(self, dataSourceId, date_stamp):
		"""
		Sync sleep data for a given day from Fitbit to Google fit.

		dataSourceId -- google fit data sourceid for activity segment
		date_stamp -- timestamp in yyyy-mm-dd format of the start day
		"""
		raise NotImplementedError('Feature not implemented yet!')

	def SyncFitbitActivitiesToGoogleFit(self, dataSourceId, start_date='', callurl=None):
		"""
		Sync activities data starting from a given day from Fitbit to Google fit.

		dataSourceId -- google fit data sourceid for activity segment
		start_date -- timestamp in yyyy-mm-dd format of the start day
		callurl -- url to fetch activities from
		"""
		# Fitbit activities list endpoint is in beta stage. It may break in the future and not directly supported
		# by the python client library.
		if not callurl:
			callurl = '{}/user/-/activities/list.json?afterDate={}&sort=asc&offset=0&limit=20'.format(self.FITBIT_API_URL,start_date)
		activities_raw = self.ReadFromFitbit(self.fitbitClient.make_request, callurl)
		activities = activities_raw['activities']

		startTimeMillis,endTimeMillis = [],[]
		for activity in activities:
			# 1. write a fit session about the activity 
			google_session = self.convertor.ConvertFitbitActivityLog(activity)
			self.WriteSessionToGoogleFit(google_session)

			# 2. create activity segment data points for the activity
			activity_segment = dict(
				dataTypeName='com.google.activity.segment',
				startTimeNanos=self.convertor.nano(google_session['startTimeMillis']),
				endTimeNanos=self.convertor.nano(google_session['endTimeMillis']),
				value=[dict(intVal=google_session['activityType'])]
				)
			self.WriteToGoogleFit(dataSourceId, [activity_segment])

			# Just for user output
			startTimeMillis.append(google_session['startTimeMillis'])
			endTimeMillis.append(google_session['endTimeMillis'])

		if len(startTimeMillis) > 0:
			print("Synced {} exercises between : {} -- {}".format(len(activities),
				datetime.datetime.fromtimestamp(min(startTimeMillis)/1000).strftime('%Y-%m-%d'),
				datetime.datetime.fromtimestamp(max(endTimeMillis)/1000).strftime('%Y-%m-%d')) )
		else:
			print("No Fitbit exercises logged since {}".format(start_date))
			return

		if activities_raw['pagination']['next'] != '':
		 	self.SyncFitbitActivitiesToGoogleFit(dataSourceId, callurl=activities_raw['pagination']['next'])

