#!/usr/bin/env python3
"""
__author__ = "Praveen Kumar Pendyala"
__email__ = "mail@pkp.io"
"""
import logging
import datetime
import time
import dateutil.parser
import json
from datetime import timedelta, date
from oauth2client.file import Storage
import parsedatetime as pdt

class Convertor:
	"""Methods for data type conversions. All fitbit conversion methods convert to google fit compatible data types"""

	# Unit conversion constants
	POUNDS_PER_KILOGRAM = 2.20462
	METERS_PER_MILE = 1609.34

	def __init__(self, googleCredsFile, googleDeveloperProjectNumber, tzinfo):
		""" Intialize a convertor object.

		googleCredsFile -- Google Fits credentials file
		tzinfo -- Timezone information of the Fitbit user
		"""
		self.googleCredsFile = googleCredsFile
		self.googleDeveloperProjectNumber = googleDeveloperProjectNumber
		self.tzinfo = tzinfo

	def UpdateTimezone(self, tzinfo):
		"""Update user's timezone info"""
		self.tzinfo = tzinfo

	#------------------------ General convertors ----------------------------

	def EpochOfFitbitTimestamp(self, timestamp, tzincluded=False):
		"""Returns a epoch time stamp (in milliseconds). Useful for converting fitbit timestamps to epoch values.

		timestamp -- date-time stamp as a string "yyyy-mm-dd hh:mm:ss" (24-hour) or any other standard format
		tzincluded -- is timezone included in the timestamp? Otherwise, timezone passed during convertor construction 
		will be used.
		"""
		dawnOfTime = datetime.datetime(1970, 1, 1, tzinfo=dateutil.tz.tzutc())
		if not tzincluded:
			logTime = dateutil.parser.parse(timestamp).replace(tzinfo=self.tzinfo)
		else:
			logTime = dateutil.parser.parse(timestamp)
		return int((logTime - dawnOfTime).total_seconds() * 1000)

	def nano(self, val):
		"""Converts epoch milliseconds to nano seconds precision"""
		return int(val * (10**6))

	def daterange(self, start_date, end_date, step=1):
		""" returns a generator that iterates from start_date to end_date. 

		step -- number of days to skip between each generated day time stamp.
		"""
		for n in range(0, int((end_date - start_date).days), step):
			yield start_date + timedelta(n)

	def parseHumanReadableDate(self,datestr):
		"""Parses a human-readable date string to python's date object"""
		cal = pdt.Calendar()
		now = datetime.datetime.now()
		return cal.parseDT(datestr, now)[0].date()


	#------------------------ Fitbit to Google Fit convertors ----------------------------

	def ConvertFibitPoint(self, date, data_point, dataType):
		"""Converts a single Fitbit data point of a given data type to Google fit data point

		date -- date to which the data_point belongs to in "yyyy-mm-dd" format
		data_point -- a single Fitbit intraday step data point
		dataType -- data type of the point
		"""
		if dataType == 'steps':
			return self.ConvertFibitStepsPoint(date, data_point)
		elif dataType == 'distance':
			return self.ConvertFibitDistancePoint(date, data_point)
		elif dataType == 'heart_rate':
			return self.ConvertFibitHRPoint(date, data_point)
		elif dataType == 'weight':
			return self.ConvertFibitWeightPoint(date, data_point)
		elif dataType == 'body_fat':
			return self.ConvertFibitBodyfatPoint(date, data_point)
		elif dataType == 'calories':
			return self.ConvertFibitCaloriesPoint(date, data_point)
		elif dataType == 'sleep':
			return self.ConvertFibitSleepPoint(date, data_point)
		else:
			raise ValueError("Unexpected data type given!")

	def ConvertFibitStepsPoint(self, date, data_point):
		"""Converts a single Fitbit intraday steps data point to Google fit data point

		date -- date to which the data_point belongs to in "yyyy-mm-dd" format
		data_point -- a single Fitbit intraday step data point
		"""
		timestamp = "{} {}".format(date, data_point['time'])
		epoch_time_nanos = self.nano(self.EpochOfFitbitTimestamp(timestamp))

		return dict(
			dataTypeName='com.google.step_count.delta',
			startTimeNanos=epoch_time_nanos,
			endTimeNanos=epoch_time_nanos+110,
			value=[dict(intVal=data_point['value'])]
			)

	def ConvertFibitDistancePoint(self, date, data_point):
		"""Converts a single Fitbit intraday distance data point to Google fit data point

		date -- date to which the data_point belongs to in "yyyy-mm-dd" format
		data_point -- a single Fitbit intraday step data point
		"""
		timestamp = "{} {}".format(date, data_point['time'])
		epoch_time_nanos = self.nano(self.EpochOfFitbitTimestamp(timestamp))
		gfit_distance = data_point['value'] * self.METERS_PER_MILE

		return dict(
			dataTypeName='com.google.distance.delta',
			startTimeNanos=epoch_time_nanos,
			endTimeNanos=epoch_time_nanos+110,
			value=[dict(fpVal=gfit_distance)]
			)

	def ConvertFibitHRPoint(self, date, data_point):
		"""Converts a single Fitbit intraday heart rate data point to Google fit data point

		date -- date to which the data_point belongs to in "yyyy-mm-dd" format
		data_point -- a single Fitbit intraday step data point
		"""
		timestamp = "{} {}".format(date, data_point['time'])
		epoch_time_nanos = self.nano(self.EpochOfFitbitTimestamp(timestamp))

		return dict(
			dataTypeName='com.google.heart_rate.bpm',
			startTimeNanos=epoch_time_nanos,
			endTimeNanos=epoch_time_nanos+110,
			value=[dict(fpVal=data_point['value'])]
			)

	def ConvertFibitCaloriesPoint(self, date, data_point):
		"""Converts a single Fitbit intraday heart rate data point to Google fit data point

		date -- date to which the data_point belongs to in "yyyy-mm-dd" format
		data_point -- a single Fitbit intraday step data point
		"""
		timestamp = "{} {}".format(date, data_point['time'])
		epoch_time_nanos = self.nano(self.EpochOfFitbitTimestamp(timestamp))

		return dict(
			dataTypeName='com.google.calories.expended',
			startTimeNanos=epoch_time_nanos,
			endTimeNanos=epoch_time_nanos+110,
			value=[dict(fpVal=data_point['value'])]
			)

	def ConvertFibitWeightPoint(self, date, data_point):
		"""Converts a single Fitbit weight log to Google fit data point

		date -- date to which the data_point belongs to in "yyyy-mm-dd" format
		data_point -- a single Fitbit intraday weight log data point
		"""
		timestamp = "{} {}".format(date, data_point['time'])
		epoch_time_nanos = self.nano(self.EpochOfFitbitTimestamp(timestamp))
		googleWeight = data_point['weight'] / self.POUNDS_PER_KILOGRAM

		return dict(
			dataTypeName='com.google.weight',
			startTimeNanos=epoch_time_nanos,
			endTimeNanos=epoch_time_nanos+110,
			value=[dict(fpVal=googleWeight)]
			)

	def ConvertFibitBodyfatPoint(self, date, data_point):
		"""Converts a single Fitbit body fat percentage data point to Google fit data point

		date -- date to which the data_point belongs to in "yyyy-mm-dd" format
		data_point -- a single Fitbit intraday step data point
		"""
		timestamp = "{} {}".format(date, data_point['time'])
		epoch_time_nanos = self.nano(self.EpochOfFitbitTimestamp(timestamp))

		return dict(
			dataTypeName='com.google.body.fat.percentage',
			startTimeNanos=epoch_time_nanos,
			endTimeNanos=epoch_time_nanos+110,
			value=[dict(fpVal=data_point['fat'])]
			)

	def ConvertFibitSleepPoint(self, date, data_point):
		"""Converts a single Fitbit intraday distance data point to Google fit data point

		date -- date to which the data_point belongs to in "yyyy-mm-dd" format
		data_point -- a single Fitbit intraday step data point
		"""
		timestamp = "{} {}".format(date, data_point['dateTime'])
		epoch_time_nanos = self.nano(self.EpochOfFitbitTimestamp(timestamp))

		# Convert sleep data point to google fit sleep types
		if data_point['value'] == 1:
			sleepType = 72
		elif data_point['value'] == 2:
			sleepType = 109
		elif data_point['value'] == 3:
			sleepType = 112
		else:
			sleepType = 72

		return dict(
			dataTypeName='com.google.activity.segment',
			startTimeNanos=epoch_time_nanos,
			endTimeNanos=epoch_time_nanos+60000000000,
			value=[dict(intVal=sleepType)]
			)


	def ConvertGFitSleepSession(self, sleep_points, logId):
		"""Converts a list of Google Fit sleep points to Google fit session 

		sleep_points -- Google Fit sleep points
		"""
		minLogMillis = min([point['startTimeNanos'] for point in sleep_points]) / 10**6
		maxLogMillis = max([point['endTimeNanos'] for point in sleep_points]) / 10**6

		return dict(
			modifiedTimeMillis=int((time.time() * 1000)),
			startTimeMillis=minLogMillis,
			endTimeMillis=maxLogMillis,
			activeTimeMillis=maxLogMillis-minLogMillis,
			description='A Fitbit sleep log',
			activityType=72,
			application=dict(name='Fbit-Gfit',detailsUrl=''),
			id='io.pkp.fbit-gfit:fitbit:{}'.format(logId),
			name='Sleep'
			)

	def ConvertFitbitActivityLog(self, activity):
		"""Converts a single Fitbit activity log to Google fit session 

		activity -- fitbit activity
		"""
		startTimeMillis = self.EpochOfFitbitTimestamp(activity['startTime'],tzincluded=True)
		endTimeMillis = startTimeMillis + activity['duration']

		# Activity type conversion
		if activity['activityName'] in ('Walk'):
			activityType = 7
		elif activity['activityName'] in ('Run','Running'):
			activityType = 8
		elif activity['activityName'] in ('Treadmill'):
			activityType = 88
		elif activity['activityName'] in ('Volleyball','Sport'):
			activityType = 89
		elif activity['activityName'] in ('Swimming', 'Swim'):
			activityType = 82
		elif activity['activityName'] in ('Badminton'):
			activityType = 10
		elif activity['activityName'] in ('Biking'):
			activityType = 1
		elif activity['activityName'] in ('Weightlifting', 'Weights', 'Workout'):
			activityType = 97
		elif activity['activityName'] in ('Hike','Hiking'):
			activityType = 35
		elif activity['activityName'] in ('Tennis'):
			activityType = 87
		elif activity['activityName'] in ('Football'):
			activityType = 28
		elif activity['activityName'] in ('Golf'):
			activityType = 32
		elif activity['activityName'] in ('Fencing'):
			activityType = 26
		elif activity['activityName'] in ('Skiing'):
			activityType = 65
		elif activity['activityName'] in ('Cross Country Skiing'):
			activityType = 67
		elif activity['activityName'] in ('Surfing'):
			activityType = 81
		elif activity['activityName'] in ('Bike', 'Biking'):
			activityType = 1
		elif activity['activityName'] in ('Mountain Bike', 'Mountain biking'):
			activityType = 15
		elif activity['activityName'] in ('Ice skating'):
			activityType = 104
		elif activity['activityName'] in ('Cricket'):
			activityType = 23
		elif activity['activityName'] in ('Dancing'):
			activityType = 24
		elif activity['activityName'] in ('Ultimate frisbee', 'Frisbee'):
			activityType = 30
		elif activity['activityName'] in ('Spinning'):
			activityType = 103
		else:
			activityType = 4 # Unknown activity

		return dict(
			modifiedTimeMillis=int((time.time() * 1000)),
			startTimeMillis=startTimeMillis,
			endTimeMillis=endTimeMillis,
			activeTimeMillis=activity['duration'],
			description='A Fitbit activity of type - {}'.format(activity['logType']),
			activityType=activityType,
			application=dict(name='Fbit-Gfit',detailsUrl=''),
			id='io.pkp.fbit-gfit:fitbit:{}'.format(activity['logId']),
			name=activity['activityName']
			)

	#------------------------  Google Fit data source generators ------------------------

	def GetDataSource(self, type='steps'):
		"""Returns a data source for Google Fit data logging
		
		type - type of data. Possible options: steps, weight, heart_rate, activity
		"""
		# Do NOT change these after the first sync!
		model,device_type = 'charge-hr', 'watch'
		if type == 'steps':
			dataType=dict(name='com.google.step_count.delta',field=[dict(name='steps',format='integer')])
		elif type == 'distance':
			dataType=dict(name='com.google.distance.delta',field=[dict(name='distance',format='floatPoint')])
		elif type == 'weight':
			dataType=dict(name='com.google.weight',field=[dict(name='weight',format='floatPoint')])
			model,device_type='aria','scale' # weighing machine
		elif type == 'body_fat':
			dataType=dict(name='com.google.body.fat.percentage',field=[dict(name='percentage',format='floatPoint')])
			model,device_type='aria','scale' # weighing machine
		elif type == 'heart_rate':
			dataType=dict(name='com.google.heart_rate.bpm',field=[dict(name='bpm',format='floatPoint')])
		elif type == 'calories':
			dataType=dict(name='com.google.calories.expended',field=[dict(name='calories',format='floatPoint')])
		elif type in ('activity','sleep'):
			dataType=dict(name='com.google.activity.segment',field=[dict(name='activity',format='integer')])
		else:
			raise ValueError("Unexpected data type given!")

		return dict(
			type='raw',
			application=dict(name='fbit-gfit'),
			dataType=dataType,
			device=dict(type=device_type,manufacturer='fitbit',model=model,
				uid='io.pkp.fbit-gfit',version='1'))

	def GetDataSourceId(self, dataType):
		"""Returns a data source id for Google Fit

		dataType -- type of data. Possible options: steps, weight, heart_rate
		"""
		dataSource = self.GetDataSource(dataType)
		#DataSourceId format
		#type:dataType.name:developer-project-number:device.manufacturer:device.model:device.uid:dataStreamName
		#reference https://developers.google.com/fit/rest/v1/reference/users/dataSources
		return ':'.join((
			dataSource['type'],
			dataSource['dataType']['name'],
			self.googleDeveloperProjectNumber,
			dataSource['device']['manufacturer'],
			dataSource['device']['model'],
			dataSource['device']['uid']))

