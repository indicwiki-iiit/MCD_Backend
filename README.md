# Micro Content Development Framework

## Overview

Micro Content Development (MCD) backend is built using Flask.

## Prerequisites

Ensure that your system meet the below requirements
- Python 3.8+
- [MongoDB](https://docs.mongodb.com/manual/installation/)

## Setting up

### Creating a virtual environment

* Create a python virtual environment that ensures above setup won't hamper the global python packages.
```shell
$ python -m venv venv
$ source venv/bin/activate
```
* Install the dependencies

```shell
$ pip install -r requirements.txt
```


### Configuring the Database

* Install the mongodb community edition.
* Once installed, check whether the `mongod` service is up and running, using the below command

```shell
$ systemctl status mongod
```

* If mongod is inactive execute the following

```shell
$ systemctl start mongod
$ systemctl enable mongod
```

* Once standard mongo setup is done, enable user authentication as follows or
follow [this](https://docs.mongodb.com/manual/tutorial/enable-authentication/):

* Invoke the mongo shell on terminal

```shell
$ mongo
```

* add user called `admin` to mongo database

```shell
use admin
db.createUser(
  {
    user: "admin",
    pwd: "test1234",
    roles: [ { role: "userAdminAnyDatabase", db: "admin" }, "readWriteAnyDatabase" ]
  }
)
```

open mongod config file and add following line to mongod config file. On ubuntu it is present
in `etc` directory: `/etc/mongod.conf`.

```
security:
    authorization: enabled
```

While opening the files one needs to have `sudo` previledges otherwise you can't edit the file.

## Running the project

Start the backend server by navigating to backend folder and then execute the run script:

```shell
$ bash run.sh
```

Testing of backend can be done using the following command.

```shell
$ pytest
```

To get more informative results for testing, run the below command. This command will display log
messages printed while running tests and will also provide the coverage report for the project.

```shell
$ pytest -v -rP --cov=src
```

To obtain all the html coverage reports for each file and the whole project, run the below command.
This will generate a `htmlcov` folder in root of backend directory.

```shell
$ coverage html
```