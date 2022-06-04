# configuring the uwsgi application
import os
from app import app


if __name__ == "__main__":
    # _debug = app.config.get('DEBUG', False)

    # kwargs = {
    #     'host': os.getenv('FLASK_HOST', '0.0.0.0'),
    #     'port': int(os.getenv('FLASK_PORT', 5003)),
    #     'debug': _debug,
    #     'use_reloader': app.config.get('USE_RELOADER', _debug),
    #     **app.config.get('SERVER_OPTIONS', {})
    # }

    app.run()
