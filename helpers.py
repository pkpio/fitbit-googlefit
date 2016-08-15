#!/usr/bin/env python
"""
helper methods to abstract few trivial / unchanging actions.
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

fitbitCredsFile = 'auth/fitbit.json'
googleCredsFile = 'auth/google.json'

def GetFitbitClient(filepath):
	"""Returns an authenticated fitbit client object

	filepath -- path to file containing oauth credentials in json format
	"""
	logging.debug("Creating Fitbit client")
	credentials = json.load(open(filepath))  
	client = fitbit.Fitbit(**credentials)
	logging.debug("Fitbit client created")
	return client, credentials

def UpdateFitbitCredentials(fitbitClient, credentials, filepath=fitbitCredsFile):
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
	# Do NOT change these after the first sync!
	model = 'charge-hr'
	if type == 'steps':
		dataType=dict(name='com.google.step_count.delta',field=[dict(name='steps',format='integer')])
	elif type == 'distance':
		dataType=dict(name='com.google.distance.delta',field=[dict(name='distance',format='floatPoint')])
	elif type == 'weight':
		dataType=dict(name='com.google.weight',field=[dict(name='weight',format='floatPoint')])
		model='aria' # weighing machine
	elif type == 'heart_rate':
		dataType=dict(name='com.google.heart_rate.bpm',field=[dict(name='bpm',format='floatPoint')])
	else:
		raise ValueError("Unexpected data type given!")

	return dict(
		type='raw',
		application=dict(name='fbit-gfit'),
		dataType=dataType,
		device=dict(type='watch',manufacturer='fitbit',model=model,
			uid='io.pkp.fbit-gfit',version='1'))

def SetCredsFilePaths(fitbitFilepath, googleFilepath):
	"""Set the default google creds file path. Allows to call GetDataSourceId with less params"""
	global fitbitCredsFile,googleCredsFile
	fitbitCredsFile,googleCredsFile = fitbitFilepath, googleFilepath

def GetDataSourceId(dataType,credsFilepath=googleCredsFile):
	"""Returns a data source id for Google Fit

	dataType -- type of data. Possible options: steps, weight, heart_rate
	credsFilepath -- path to file containing Google oauth credentials
	"""
	dataSource = GetDataSource(dataType)
	projectNumber = Storage(credsFilepath).get().client_id.split('-')[0]
	return ':'.join((
		dataSource['type'],
		dataSource['dataType']['name'],
		projectNumber,
		dataSource['device']['manufacturer'],
		dataSource['device']['model'],
		dataSource['device']['uid']))
