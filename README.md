# Introduction
----------------------------
Export all your Fitbit data to Google Fit. Unlike other alternatives such as fitnessyncer.com, this aims to offer very fine granularity for data. Check all the features, setup and usage instructions below.


# Features
----------------------------
- [x] Steps - minute level precision
- [x] Distance - minute level precision
- [x] Heart rate - second level precision
- [x] Weight
- [x] Body fat
- [x] Activities 
  - [x] Running
  - [x] Swimming
  - [x] Biking
  - [x] Volleyball
  - [x] Walking
  - [x] Badminton
  - [x] Workouts (as weightlifting)
- [x] Calories - minute level precision
- [ ] Floors - minute level precision
- [ ] Elevation - minute level precision
- [ ] Food logs


# Setup
----------------------------
You have to register your own Fitbit and Google Fit applications. This setup is a one time thing.

1. Fitbit setup
-------------------
All instructions below must be performed using the same Fitbit account you want to sync with Google Fit.

- Register a new Fitbit application at https://dev.fitbit.com/apps/new
- Use the information below:

```
Application Name : --
Description : --
Application Website : --
Organization : --
Organization Website : --
OAuth 2.0 Application Type : Personal
Callback URL : http://localhost:8080/
Default Access Type : Read-Only

Note : Use your own information for ```--``` but make sure you copy the Callback URL exactly (including the last /)
```
- Hit save and make a note of ```OAuth 2.0 Client ID``` and ```Client Secret```
- Go to /auth and run ```python3 auth_fitbit.py <client-id> <client-secret>```
- This opens a popup in the browser. Authenticate and done!


2. Google Fit setup
-------------------

