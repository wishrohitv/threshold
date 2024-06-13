#!/bin/sh
source .venv/bin/activate
export PYTHONDONTWRITEBYTECODE=1

python -m flask --app run run -p $PORT --debug 

# 1st run is run.py file and 2nd run is flask command