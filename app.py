import configparser
import fitbit

# Read configuration data
config = configparser.ConfigParser()
config.read('config-local.ini')

# Fibit config
fitbit_conf = config['fitbit']
fitbit_key = fitbit_conf.get('key')
fitbit_secret = fitbit_conf.get('secret')
fitbit_access_token = fitbit_conf.get('access_token')
fitbit_refresh_token = fitbit_conf.get('refresh_token')

# Setup a fitbit client
fitbit_client = fitbit.Fitbit(fitbit_key, fitbit_secret, 
	access_token=fitbit_access_token, refresh_token=fitbit_refresh_token)

# certain methods do not require user keys
print(fitbit_client.intraday_time_series('activities/steps'))
