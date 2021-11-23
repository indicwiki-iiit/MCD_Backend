import os


class Config:
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "secret")

    DB_URL = os.getenv('DB_URL', 'localhost')  # DB HOST
    DB_USER = os.getenv('DB_USER', 'admin')  # We should not set this things default
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'test1234')  # We should not set this things default
    DB_PORT = os.getenv('DB_PORT', 27017)
    DB_NAME = os.getenv('DB_NAME', 'mcdDB')
    DB_DEPLOYMENT = 'local'

    SERVER_PORT = os.getenv('SERVER_PORT', 9000)
    SERVER_LOG_LEVEL = 'debug'
