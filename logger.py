import logging
from logging.handlers import RotatingFileHandler

class logger(object):
    def __init__(self, context=None, **kwargs):
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
        logging.basicConfig(level=file_level,
                            format=file_format,
                            datefmt='%m-%d %H:%M:%S',
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

    def logger_init_v0(self, console_level, file_level, log_file, logger_name):
        file_format = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
        console_format = '%(name)-12s: %(levelname)-6s %(message)s'
        logging.basicConfig(level=file_level,
                            format=file_format,
                            datefmt='%m-%d %H:%M:%S',
                            filename=log_file,
                            filemode='a')
        console = logging.StreamHandler()
        console.setLevel(console_level)
        # set a format which is simpler for console use
        formatter = logging.Formatter(console_format)
        # tell the handler to use this format
        console.setFormatter(formatter)
        # add the handler to the root logger
        logging.getLogger('').addHandler(console)
        # add rotate handler
        rotate_handler = RotatingFileHandler(log_file, 
                                             maxBytes=100000000, 
                                             backupCount=5)
        logging.getLogger('').addHandler(rotate_handler)
        logger_handle = logging.getLogger(logger_name)
        return logger_handle
