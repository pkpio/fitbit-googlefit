FROM python:jessie

RUN mkdir /fitbit-googlefit/
WORKDIR /fitbit-googlefit/

COPY requirements.txt /fitbit-googlefit/requirements.txt
RUN pip install -r requirements.txt

COPY . /fitbit-googlefit/

CMD python3 app.py

# Use with the following command: 
# $ docker run --rm -it -v /path/to/auth/fitbit.json:/fitbit-googlefit/auth/fitbit.json -v /path/to/auth/google.json:/fitbit-googlefit/auth/google.json praveendath92/fitbit-googlefit

