#!/bin/bash

# run the below command in python environment with installed package listed in ../requirement.txt
PYTHON=$(which python)
FLASK_APP=$PWD/app.py FLASK_ENV=development $PYTHON -m flask run --port 4433

