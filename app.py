import builtins as __builtin__
import os
from src import create_app

# allows you to copy json snippets directly into python
__builtin__.true = True
__builtin__.false = False
__builtin__.null = None

basestring = getattr(__builtins__, 'basestring', str)


def config_str_to_obj(cfg):
    if isinstance(cfg, basestring):
        module = __import__('config', fromlist=[cfg])
        return getattr(module, cfg)
    return cfg


def app_factory(config_obj_path):
    app = create_app()
    config = config_str_to_obj(config_obj_path)
    app.config.from_object(config)
    return app


# def heroku():
    # return app_factory('Config')


config_obj_path = ''

try:
    config_obj_path = os.environ.get('FLASK_CONFIG_DEFAULT')
except KeyError:
    print(
        "Please, provide the environment variable FLASK_CONFIG_DEFAULT. "
        "It tells the application which configuration class to load.")
    exit()

app = app_factory(config_obj_path)
print('*************************')


if __name__ == "__main__":


    kwargs = {
        'host':'0.0.0.0',
        'port': 5000,
        'debug': True,
        'use_reloader': app.config.get('USE_RELOADER', app.debug == True),
        **app.config.get('SERVER_OPTIONS', {})
    }

    app.run(**kwargs)

    # app.run()

