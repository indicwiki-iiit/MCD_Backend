import logging
import os

PROJECT_NAME = "mcd"


class Config:
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', True)

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "secret")

    WTF_CSRF_ENABLED = True

    TESTING = False

    SERVER_OPTIONS = {}

    DB_DEPLOYMENT_ENV = os.getenv('DB_DEPLOYMENT_ENV', 'development')

    MONGODB_USER = os.getenv('MONGODB_USER', '')
    MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD', '')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', '')
    MONGODB_PORT = os.getenv('MONGODB_PORT', 27017)

    # LOGGING
    # LOGGER_NAME = "%s_log" % PROJECT_NAME
    # LOG_FILENAME = "/var/tmp/app.%s.log" % PROJECT_NAME
    # LOG_LEVEL = logging.INFO
    # LOG_FORMAT = "%(asctime)s %(levelname)s\t: %(message)s"


class DevConfig(Config):
    pass


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
