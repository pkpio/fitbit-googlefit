#!/usr/bin/env python
"""
This was taken, and modified from python-fitbit/gather_keys_oauth2.py,
License reproduced below.

--------------------------
Copyright 2012-2015 ORCAS

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import os
import sys
import threading
import traceback
import webbrowser
import json

from base64 import b64encode
import cherrypy
from fitbit.api import FitbitOauth2Client
from oauthlib.oauth2.rfc6749.errors import MismatchingStateError, MissingTokenError
from requests_oauthlib import OAuth2Session
import argparse
import urllib.parse as urlparse

class OAuth2Server:
    def __init__(self, client_id, client_secret,
                 redirect_uri='http://localhost:8080/'):
        """ Initialize the FitbitOauth2Client """
        self.redirect_uri = redirect_uri
        self.success_html = """
            <h1>You are now authorized to access the Fitbit API!</h1>
            <br/><h3>You can close this window</h3>"""
        self.failure_html = """
            <h1>ERROR: %s</h1><br/><h3>You can close this window</h3>%s"""
        self.oauth = FitbitOauth2Client(client_id, client_secret)

    def browser_authorize(self):
        """
        Open a browser to the authorization url and spool up a CherryPy
        server to accept the response
        """
        url, _ = self.oauth.authorize_token_url(redirect_uri=self.redirect_uri)
        # Open the web browser in a new thread for command-line browser support
        threading.Timer(1, webbrowser.open, args=(url,)).start()
        cherrypy.quickstart(self)

    def headless_authorize(self):
        """
        Authorize without a display using only TTY.
        """
        url, _ = self.oauth.authorize_token_url(redirect_uri=self.redirect_uri)
        # Ask the user to open this url on a system with browser
        print('\n-------------------------------------------------------------------------')
        print('\t\tOpen the below URL in your browser\n')
        print(url)
        print('\n-------------------------------------------------------------------------\n')
        print('NOTE: After authenticating on Fitbit website, you will redirected to a URL which ')
        print('throws an ERROR. This is expected! Just copy the full redirected here.\n')
        redirected_url = input('Full redirected URL: ')
        params = urlparse.parse_qs(urlparse.urlparse(redirected_url).query)
        print(params['code'][0])
        self.authenticate_code(code=params['code'][0])

    @cherrypy.expose
    def index(self, state, code=None, error=None):
        """
        Receive a Fitbit response containing a verification code. Use the code
        to fetch the access_token.
        """
        error = None
        if code:
            self.authenticate_code(code=code)
        else:
            error = self._fmt_failure('Unknown error while authenticating')
        # Use a thread to shutdown cherrypy so we can return HTML first
        self._shutdown_cherrypy()
        return error if error else self.success_html

    def authenticate_code(self, code=None):
        """
        Final stage of authentication using the code from Fitbit.
        """
        try:
            self.oauth.fetch_access_token(code, self.redirect_uri)
        except MissingTokenError:
            error = self._fmt_failure(
                'Missing access token parameter.</br>Please check that '
                'you are using the correct client_secret'
            )
        except MismatchingStateError:
            error = self._fmt_failure('CSRF Warning! Mismatching state')

    def _fmt_failure(self, message):
        tb = traceback.format_tb(sys.exc_info()[2])
        tb_html = '<pre>%s</pre>' % ('\n'.join(tb)) if tb else ''
        return self.failure_html % (message, tb_html)

    def _shutdown_cherrypy(self):
        """ Shutdown cherrypy in one second, if it's running """
        if cherrypy.engine.state == cherrypy.engine.states.STARTED:
            threading.Timer(1, cherrypy.engine.exit).start()


def main():
    # Arguments parsing
    parser = argparse.ArgumentParser("Client ID and Secret are mandatory arguments")
    parser.add_argument("-i", "--id", required=True, help="Client id")
    parser.add_argument("-s", "--secret", required=True, help="Client secret")
    parser.add_argument("-c", "--headless", default=False, 
        help="Authenticate only using console (for headless systems)", action="store_true")
    args = parser.parse_args()

    server = OAuth2Server(args.id, args.secret)
    if(args.headless):
        server.headless_authorize()
    else:   
        server.browser_authorize()

    credentials = dict(
        client_id=args.id,
        client_secret=args.secret,
        access_token=server.oauth.token['access_token'],
        refresh_token=server.oauth.token['refresh_token'])
    json.dump(credentials, open('fitbit.json', 'w'))

if __name__ == '__main__':
    main()
