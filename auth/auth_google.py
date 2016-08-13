#!/usr/bin/env python
import sys

from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run_flow, argparser

def main():
  client_id = sys.argv[1]
  client_secret = sys.argv[2]

  # Scopes of authorization
  activity = "https://www.googleapis.com/auth/fitness.activity.write"
  body = "https://www.googleapis.com/auth/fitness.body.write"
  location = "https://www.googleapis.com/auth/fitness.location.write"
  scopes = activity + " " + body + " " + location

  flow = OAuth2WebServerFlow(client_id, client_secret, scopes)
  storage = Storage('google.json')
  flags = argparser.parse_args([])
  run_flow(flow, storage, flags)

if __name__ == '__main__':
  main()
