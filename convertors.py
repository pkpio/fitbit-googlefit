#!/usr/bin/env python

"""
Methods for data type conversions. All fitbit conversion method convert 
to google fit compatible data types
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

# Unit conversion constants
POUNDS_PER_KILOGRAM = 2.20462
METERS_PER_MILE = 1609.34

#------------------------ General convertors ----------------------------

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

def daterange(start_date, end_date, step=1):
	""" returns a generator that iterates from start_date to end_date. 

	step -- number of days to skip between each generated day time stamp.
	"""
	for n in range(0, int((end_date - start_date).days), step):
		yield start_date + timedelta(n)


#------------------------ Fitbit to Google Fit convertors ----------------------------

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

def ConvertFibitWeightPoint(date, data_point, tzinfo):
	"""Converts a single Fitbit weight log to Google fit data point

	date -- date to which the data_point belongs to in "yyyy-mm-dd" format
	data_point -- a single Fitbit intraday weight log data point
	tzinfo --  time zone information of the user
	"""
	timestamp = "{} {}".format(date, data_point['time'])
	epoch_time_nanos = nano(EpochOfFitbitTimestamp(timestamp, tzinfo))
	googleWeight = data_point['weight'] / POUNDS_PER_KILOGRAM

	return dict(
		dataTypeName='com.google.weight',
		startTimeNanos=epoch_time_nanos,
		endTimeNanos=epoch_time_nanos+110,
		value=[dict(fpVal=googleWeight)]
		)

