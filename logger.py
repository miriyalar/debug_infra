import logging
from logging.handlers import RotatingFileHandler
c_level = logging.ERROR
_loggers = {}

def getLogger(logger_name=None, console_level=None, **kwargs):
    global c_level
    c_level = console_level or c_level
    if logger_name not in _loggers:
        _loggers[logger_name] = logger(logger_name=logger_name,
                                       console_level=c_level, **kwargs)
    return _loggers[logger_name].get_logger()

class logger(object):
    def __init__(self, **kwargs):
        console_level = kwargs.get('console_level', logging.ERROR)
        file_level = kwargs.get('file_level', logging.DEBUG)
        log_file = kwargs.get('log_file', './debug_nodes.log')
        logger_name = kwargs.get('logger_name', None)
        self.logger = self.logger_init(console_level, file_level, log_file, logger_name)

    def get_logger(self):
        return self.logger

    def logger_init(self, console_level, file_level, log_file, logger_name):
        file_format = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
        console_format = '%(name)-12s: %(levelname)-6s %(message)s'
        logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARN)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
        logging.getLogger('urllib3.util.retry').setLevel(logging.WARN)
        logging.basicConfig(level=file_level,
                            format=file_format,
                            datefmt='%m-%d-%y %H:%M:%S %Z',
                            filename=log_file,
                            filemode='w')
        console = logging.StreamHandler()
        console.setLevel(console_level)
        # set a format which is simpler for console use
        formatter = logging.Formatter(console_format)
        # tell the handler to use this format
        console.setFormatter(formatter)

        # add rotate handler
        rotate_handler = RotatingFileHandler(log_file,
                                             maxBytes=100000000,
                                             backupCount=5)
        logger_handle = logging.getLogger(logger_name)
        logger_handle.addHandler(console)
        logger_handle.addHandler(rotate_handler)
        return logger_handle
