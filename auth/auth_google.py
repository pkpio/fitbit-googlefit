#!/usr/bin/env python
import sys
import argparse

from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run_flow, argparser

def main():
    # Arguments parsing
    parser = argparse.ArgumentParser("Client ID and Secret are mandatory arguments")
    parser.add_argument("-i", "--id", required=True, help="Client id", metavar='<client-id>')
    parser.add_argument("-s", "--secret", required=True, help="Client secret", 
        metavar='<client-secret>')
    parser.add_argument("-c", "--console", default=False, 
        help="Authenticate only using console (for headless systems)", action="store_true")
    args = parser.parse_args()

    # Scopes of authorization
    activity = "https://www.googleapis.com/auth/fitness.activity.write"
    body = "https://www.googleapis.com/auth/fitness.body.write"
    location = "https://www.googleapis.com/auth/fitness.location.write"
    scopes = activity + " " + body + " " + location

    flow = OAuth2WebServerFlow(args.id, args.secret, scopes)
    storage = Storage('google.json')
    flags = ['--noauth_local_webserver'] if args.console else []
    run_flow(flow, storage, argparser.parse_args(flags))

if __name__ == '__main__':
    main()
