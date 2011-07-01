"""
Logging facilities to combine the advantges of both Python's standard logging
module and Twisted's logging facility.
"""


from __future__ import absolute_import

from datetime import datetime

import logging
import sys

from twisted.python import log


# Shut PyLint to complain about * and ** magic
# pylint: disable-msg=W0142


def printFormatted(event, stream, severity=0):
    eventSeverity = event.get('severity', logging.INFO)

    if eventSeverity < severity:
        return

    # {timestamp:%Y-%m-%d %H:%M:%S}
    # 'timestamp': event.get('timestmap', datetime.now()),

    indent = ' ' * (15 + len(event['system']))

    message = ' '.join(event['message'])
    message = '\n'.join([indent + l for l in message.splitlines()])
    message = message.lstrip()

    stream.write('{severity:>10s}: [{system}] {message}\n'.format(**{
        'severity': logging.getLevelName(eventSeverity),
        'system': event['system'],
        'message': message,
    }))



class StdioOnnaStick(log.StdioOnnaStick, object):
    
    def __init__(self, callback):
        super(StdioOnnaStick, self).__init__(0)
        self.callback = callback

    def write(self, data):
        d = (self.buf + data).split('\n')
        self.buf = d[-1]
        messages = d[0:-1]
        for message in messages:
            self.callback(message, printed=1)

    def writelines(self, lines):
        for line in lines:
            self.callback(line, printed=1)



class Logger(object):

    # TODO: Change the use a local LogPublisher (or extend from) instead of 
    #       the global log and err functions of the t.p.log module

    def __init__(self, name='', **kwargs):
        self.name = name
        self.config = kwargs
        self.config['name'] = name

    # ------------------------------------------------------------------------
    #
    #

    def captureStdout(self):
        sys.stdout = StdioOnnaStick(self.info)
        sys.stderr = StdioOnnaStick(self.error)


    def addObserver(self, callable, *args, **kwargs):
        def observer(event):
            if event.get('name', '').startswith(self.name):
                callable(event, *args, **kwargs)

        log.addObserver(observer)


    # ------------------------------------------------------------------------
    # General reporting facilities as exposed by twisted
    #

    def log(self, msg, *args, **kwargs):
        config = self.config.copy()
        config.update(kwargs)
        config['timestamp'] = datetime.now()

        if isinstance(msg, basestring) and args:
            msg = msg.format(*args)
        elif args:
            raise TypeError('The msg parameter is not a string but ' \
                    'formatting parameters were passed in')

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

