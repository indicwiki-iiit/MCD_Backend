from pymongo import MongoClient

from config import Config
from src.logger import MyLogger

# setting up the logger
if Config.DB_DEPLOYMENT_ENV == 'production':
    logger = MyLogger('main', './server.log', use_stdout=True)
else:
    logger = MyLogger('main', './server.log', use_stdout=True)

# logger.debug('configurations applied : %s' % Config)

if Config.DB_DEPLOYMENT_ENV == 'production':
    mongo_uri = "mongodb+srv://{user}:{password}@{hostname}/{name}?retryWrites=true&w=majority".format(
        user=Config.MONGODB_USER, password=Config.MONGODB_PASSWORD,
        hostname=Config.MONGODB_HOSTNAME, name=Config.MONGODB_DB_NAME)
    # defer the immediate connection to mongodb
    # fixes the connection error while using uwsgi
    # refer: https://stackoverflow.com/questions/54778245/timeout-with-flask-uwsgi-nginx-app-using-mongodb
else:
    mongo_uri = "mongodb://{user}:{password}@{hostname}:{port}".format(
        user=Config.MONGODB_USER, password=Config.MONGODB_PASSWORD,
        hostname='db',
        port=Config.MONGODB_PORT)


logger.info(f'[{Config.DB_DEPLOYMENT_ENV}] connecting to remote database : {Config.MONGODB_DB_NAME}')
connect_flag = Config.DB_DEPLOYMENT_ENV == 'development'

mongo_db = None

# print(Config.MONGODB_USER, '##')

if Config.MONGODB_USER != '':
    # print(mongo_uri, '$$')
    mongo_db = MongoClient(mongo_uri, connect=connect_flag)[Config.MONGODB_DB_NAME]
# 

# client = MongoClient(host='mongodb',
#                          port=27017, 
#                          username='admin' ,
#                          password='admin',
#                         authSource="admin")
# mongo_db = client["mcd"]