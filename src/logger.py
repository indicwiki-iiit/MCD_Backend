from datetime import datetime
import os

LOG_LEVELS = {
    'debug': 1,
    'info': 2,
    'warn': 3,
    'critical': 4,
    'error': 5
}


class MyLogger():
    def __init__(self, name, log_file_path, use_stdout=False, overwrite=True, log_level=LOG_LEVELS['info']):
        self.name = name
        self.log_file_path = log_file_path
        self.stdout = use_stdout
        self.level = LOG_LEVELS.get(
            log_level.strip().lower(), LOG_LEVELS['info'])
        # only zero rank process can truncate the file
        if overwrite == 0:
            # truncate the file
            with open(self.log_file_path, 'w') as log_file:
                pass

    def _log_msg(self, msg, level):
        if LOG_LEVELS[level] >= self.level:
            present_time = datetime.now()
            msg_str = '%s [%s] %s' % (present_time.strftime(
                '%m/%d/%Y %I:%M:%S %p'), level, msg)
            if self.stdout:
                print(msg_str)
            with open(os.path.abspath(self.log_file_path), 'a+') as log_file:
                log_file.write(msg_str+"\n")

    def info(self, msg):
        self._log_msg(msg, 'info')

    def critical(self, msg):
        self._log_msg(msg, 'critical')

    def debug(self, msg):
        self._log_msg(msg, 'debug')

    def warn(self, msg):
        self._log_msg(msg, 'warn')

    def error(self, msg):
        self._log_msg(msg, 'error')


def logger_wrapper(logger, logger_name):
    if isinstance(logger, MyLogger):
        return logger
    base_dir = os.path.dirname(os.path.realpath(__file__))
    log_dir = os.path.join(base_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    return MyLogger(logger_name, os.path.join(log_dir, "%s.log" % logger_name), use_stdout=True, overwrite=True)
