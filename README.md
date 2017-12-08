**Promo**: Have a resolution to run/bike at least X kilometers this year? Checkout [fitgoal](https://fitgoal.herokuapp.com/) - it helps you keep track of your yearly distance covered with a neat graph. Preview [my graph](http://fitgoal.herokuapp.com/graphs/347TCH).

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

1. Run App.py
-------------------
This is a python3 application so install all the dependencies 

- Make sure you have Python 3.5 or higher installed ```sudo apt update && sudo apt install python3```
- Make sure you have Virtualenv installed ```sudo apt install virtualenv```
- Clone the repository and cd into it (cd where you want it saved at first) ```git clone https://github.com/praveendath92/fitbit-googlefit.git && cd ./fitbit-googlefit```
- Run app.py ```python3 app.py```

App.py will now create a virtualenv called fitbitenv, source this new virtualenv, and use pip3 to install its necessary dependencies.


2. Edit your config.ini
-------------------
App.py will copy ```config.template.ini``` to ```config.ini``` and attempt to open it using either ```$EDITOR```, nano, vim, or vi. If none of those are installed.

You will get a chance to press Ctrl+c to stop the script so you can edit ```config.ini```. run ```python app.py``` again after you have edited ```config.ini```, ONLY if you had to press Ctrl+c to manually edit it.

Feel free to change any settings in ```config.ini```, and if you mess it up beyond all recognition, just run ```cp -f config.template.ini config.ini``` from the ```fitbit-googlefit``` directory.

3. Fitbit setup
-------------------
All instructions below must be performed using the same Fitbit account you want to sync with Google Fit.

- Register a new Fitbit application on [Fitbit Developers Console](https://dev.fitbit.com/apps/new)
- Use the information below:

```
===========================================================================
===========================================================================

Go to this site and register a new Fitbit app
https://dev.fitbit.com/apps/new


Application Name :              --Choose a name--
Description :                   --Choose a description--
Application Website :           --Your website--
Organization :                  --Choose an organization--
Organization Website :          --Your website--
OAuth 2.0 Application Type :    **Must choose 'Personal'**
Callback URL :                  http://localhost:8080/
Default Access Type :           Read-Only

Note :
1. Use your own information for fields marked --
2. Make sure you copy the Callback URL exactly (including the last /)
3. Application Type MUST be Personal

===========================================================================
===========================================================================
```

- Hit save and make a note of ```OAuth 2.0 Client ID``` and ```Client Secret```
- Answer the questions that pop up:
  Does your computer have a native display and browser? yes or no
      If running headless on a server, select ```no```.
      If running from a desktop/laptop/Raspberry Pi (with a monitor connected directly to it), select ```yes```
- If you choose yes, a browser will show up asking you to log in. Authenticate and done!
- If you choose no, copy the url given into a browser on your phone, desktop, etc. Authenticate and then copy the redirected URL back into the program. Please make double sure that the URLs are exactly the same and you don't miss type anything if you can't copy/paste it.


4. Google Fit setup
-------------------
- Go to the [Google Developers Console](https://console.developers.google.com/flows/enableapi?apiid=fitness)
- Click ```Continue```. Then select ```Go to credentials``` and select ```Client ID```
- Under Application type, select ```Other``` and hit ```Create```
- Make a note of ```client ID``` and ```client secret```

- Copy/Paste your ```Client ID``` and ```Client Secret``` into the program when asked
- If using the browser method, follow the on screen prompts and you'll be redirected back to the program, authenticated and already preforming your initial sync.
- If using the headless method, please copy the provided url into a browser and follow the on screen prompts. Google will give you a authentication code, please copy/paste that back into the program when prompted.


# Usage
----------------------------
Use ```python3 app.py``` to initiate a manual sync.

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
This program fully supports running headless on a remote server, Raspberry Pi, Digitalocean, etc. Simply answer ```no``` when asked during set if your computer has a native display and browser. Assuming you are SSHed into the remote server, just copy the supplied URLs and paste them into your local browser, and then copy the Redirect URL (Fitbit) and Authentication Code (Google) back into the program.

Note : 
-------
1. Get command line help using the ```-h``` flag. 
2. Arguments passed through command-line take higher priority over ```config.ini``` values.
