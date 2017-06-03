**Promo**: Have a resolution to run/bike at least X kilometers this year? Checkout [fitgoal](https://fitgoal.herokuapp.com/) - it helps you keep track of your yearly distance covered with a neat graph. See [preview](https://fitgoal.herokuapp.com/graphs/praveen).

# Introduction
----------------------------
Export all your Fitbit data to Google Fit. If you find this useful, please **star** :star: the repository on Github.

Unlike other alternatives, such as fitnessyncer.com, this aims to offer very fine granularity for the data.

![Fitbit Steps](/screenshots/fitbit_steps.png "Fitbit steps")
![GoogleFit Steps](/screenshots/googlefit_steps.png "Google Fit steps")
![demo](http://i.giphy.com/3oz8xKllkMr9PrRSMw.gif)

# Features
----------------------------
- [x] Steps - minute level precision
- [x] Distance - minute level precision
- [x] Heart rate - second level precision
- [x] Weight
- [x] Body fat percentage
- [x] Activities 
  - [x] Running
  - [x] Swimming
  - [x] Biking
  - [x] Volleyball
  - [x] Walking
  - [x] Badminton
  - [x] Workouts
  - [x] Fencing
  - [x] Cricket
  - [x] Football
  - [x] Hiking
  - [x] And a [few others][activities] -- suggestions welcome!
- [x] Calories - minute level precision
- [x] Sleep logs - minute level precision
- [ ] Floors - minute level precision
- [ ] Elevation - minute level precision
- [ ] Food logs

[activities]:https://github.com/praveendath92/fitbit-googlefit/blob/master/convertors.py#L201-L241

# Setup
----------------------------
You have to register your own Fitbit and Google Fit applications. This setup is a one time thing.

1. Install dependencies
-------------------
This is a python3 application so install all the dependencies using ```sudo pip3 install -r requirements.txt```


2. Fitbit setup
-------------------
All instructions below must be performed using the same Fitbit account you want to sync with Google Fit.

- Register a new Fitbit application on [Fitbit Developers Console](https://dev.fitbit.com/apps/new)
- Use the information below:

```
Application Name : --
Description : --
Application Website : --
Organization : --
Organization Website : --
OAuth 2.0 Application Type : **Personal**
Callback URL : http://localhost:8080/
Default Access Type : Read-Only

Note : 
1. Use your own information for fields marked --
2. Make sure you copy the Callback URL exactly (including the last /)
3. Application Type MUST be Personal
```
- Hit save and make a note of ```OAuth 2.0 Client ID``` and ```Client Secret```
- ```cd /auth``` and run ```python3 auth_fitbit.py -i <client-id> -s <client-secret>```
- This opens a popup in the browser. Authenticate and done!


3. Google Fit setup
-------------------
- Go to the [Google Developers Console](https://console.developers.google.com/flows/enableapi?apiid=fitness)
- Click ```Continue```. Then select ```Go to credentials``` and select ```Client ID```
- Under Application type, select ```Other``` and hit ```Create```
- Make a note of ```client ID``` and ```client secret```
- ```cd /auth``` and run ```python3 auth_google.py -i <client-id> -s <client-secret>```
- This opens a popup in the browser. Authenticate and done!


# Usage
----------------------------
Update the ```config.ini``` with own choices and start the sync using ```python3 app.py```

Sync examples:
--------------
- With date stamps : ```python3 app.py -s 2016-08-20 -e 2016-08-22```
- Last 3 days : ```python3 app.py -s "2 days ago" -e tomorrow```
- January month : ```python3 app.py -s "jan 1 2016" -e "feb 1 2016"```

Setup autosync:
--------------
You can setup a cron task to automatically sync everyday at 2:30 AM.

```30 2 * * * /path-to-repo/fitbit-googlefit/cron.sh >> /path-to-repo/fitbit-googlefit/cron.log 2>&1```

Add above line to your cron tab: ```crontab -e``` in Linux. Sync logs will be stored to ```cron.log``` in repository.


# Headless authentication
----------------------------
If you want to do the authentication process on a system without a display - such as a raspberry pi or a remote server, pass `--console` or `-c` option to the authentication scripts. See below examples.

`python3 auth_fitbit.py -i clientid -s clientsecret --console`

`python3 auth_google.py -i clientid -s clientsecret --console`

Note : 
-------
1. Get command line help using the ```-h``` flag. 
2. Arguments passed through command-line take higher priority over ```config.ini``` values.
