#!/bin/sh

cd $(dirname $0)
. fitbitenv/bin/activate
python3 app.py

