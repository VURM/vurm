from __future__ import absolute_import

from twisted.python import log
import logging
import sys
from datetime import datetime



class Logger(object):

    def __init__(self, name='', **kwargs):
        self.name = name
        self.config = kwargs
        self.config['name'] = name

    # ------------------------------------------------------------------------
    #
    #

    def captureStdout(self):
        sys.stdout = log.logfile
        sys.stderr = log.logerr


    def printFormatted(self, event):
        # {timestamp:%Y-%m-%d %H:%M:%S}
        # 'timestamp': event.get('timestmap', datetime.now()),

        indent = ' ' * (15 + len(event['system']))

        message = ' '.join(event['message'])
        message = '\n'.join([indent + l for l in message.splitlines()])
        message = message.lstrip()

        sys.__stdout__.write('{severity:>10s}: [{system}] {message}\n'.format(**{
            'severity': logging.getLevelName(event.get('severity', logging.INFO)),
            'system': event['system'],
            'message': message,
        }))


    def addObserver(self, callable, severity=0):
        def observer(event):
            eventName = event.get('name', '')
            eventSeverity = event.get('severity', logging.WARNING)
            
            if eventName.startswith(self.name) and eventSeverity >= severity:
                callable(event)

        log.addObserver(observer)

    # ------------------------------------------------------------------------
    # General reporting facilities as exposed by twisted
    #

    def log(self, msg, *args, **kwargs):
        config = self.config.copy()
        config.update(kwargs)
        config['timestamp'] = datetime.now()

        if isinstance(msg, basestring):
            msg = msg.format(*args)
        else:
            msg = unicode(msg)

        log.msg(msg, **config)


    def exception(self, _stuff=None, _why=None, *args, **kwargs):
        config = self.config.copy()
        config.update(kwargs)
        config['timestamp'] = datetime.now()
        log.err(_stuff, _why.format(*args), **config)


    # ------------------------------------------------------------------------
    # Level specific reporting facilities as exposed by the python standard
    # library logging module
    #

    def debug(self, msg, *args, **kwargs):
        kwargs['severity'] = logging.DEBUG
        self.log(msg, *args, **kwargs)


    def info(self, msg, *args, **kwargs):
        kwargs['severity'] = logging.INFO
        self.log(msg, *args, **kwargs)


    def warning(self, msg, *args, **kwargs):
        kwargs['severity'] = logging.WARNING
        self.log(msg, *args, **kwargs)
    warn = warning

    def error(self, msg, *args, **kwargs):
        kwargs['severity'] = logging.ERROR
        self.log(msg, *args, **kwargs)
    err = error

    def critical(self, msg, *args, **kwargs):
        kwargs['severity'] = logging.CRITICAL
        self.log(msg, *args, **kwargs)
