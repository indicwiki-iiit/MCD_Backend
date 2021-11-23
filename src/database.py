import os
from pymongo import MongoClient

from src.logger import MyLogger
# from parse_config import
from config import Config

# config = get_config()
# setting up the logger
if Config.DB_DEPLOYMENT == 'production':
    logger = MyLogger('main', os.path.join('/', 'tmp', '../server.log'), use_stdout=True,
                      log_level=Config.SERVER_LOG_LEVEL)
else:
    logger = MyLogger('main', '../server.log', use_stdout=True,
                      log_level=Config.SERVER_LOG_LEVEL)

logger.debug('configurations applied : %s' % Config)

if Config.DB_DEPLOYMENT == 'production':
    mongo_uri = "mongodb+srv://{user}:{password}@{server}".format(
        user=Config.DB_DEPLOYMENT, password=Config.DB_PASSWORD, server=Config.DB_URL)
    logger.info('[PRODUCTION] connecting to remote database : %s' % Config.DB_URL)
    # defer the immediate connection to mongodb
    # fixes the connection error while using uwsgi
    # refer: https://stackoverflow.com/questions/54778245/timeout-with-flask-uwsgi-nginx-app-using-mongodb
    connect_flag = False
else:
    mongo_uri = "mongodb://{user}:{password}@{server}:{port}".format(
        user=Config.DB_USER, password=Config.DB_PASSWORD, server=Config.DB_URL,
        port=Config.DB_PORT)
    logger.info("[LOCAL] connecting to database : %s" % mongo_uri)
    connect_flag = True

mongo_db = MongoClient(mongo_uri, connect=connect_flag)[Config.DB_NAME]
