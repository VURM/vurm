"""
Logging facilities to combine the advantges of both Python's standard logging
module and Twisted's logging facility.
"""



# Shut PyLint to complain about * and ** magic.
# pylint: disable-msg=W0142

# Shut PyLint to complain about the module importing itself (the __future__
# import is not correctly handled).
# pylint: disable-msg=W0406

# Shut PyLint to complain about undefined names in the logging module (the
# __future__ import is not correctly handled).
# pylint: disable-msg=E1101



from __future__ import absolute_import

from datetime import datetime

import logging
import sys

from twisted.python import log



def printFormatted(event, stream, severity=0):
    """
    Log observer to print a formatted log entry to the console. The format is
    suitable for interactive reading but not so good for file based output.
    """

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
    """
    A class that pretends to be a file object and instead executes a callback
    for each line written to it.
    """

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
    """
    A logging class to combine features from both Python's logging system and
    Twisted's logging facility in one place.
    """

    # TODO: Change the use a local LogPublisher (or extend from) instead of
    #       the global log and err functions of the t.p.log module

    def __init__(self, name='', **kwargs):
        """
        Constructs a new logger which filters events for the given name. An
        empty string (the default) can be used to disable filtering and capture
        all events.

        All keyword arguments will be set as keys in the dictionary of each
        log event sent by this logger.
        """

        self.name = name
        self.config = kwargs
        self.config['name'] = name


    def captureStdout(self):
        """
        Sends data written to the standard output and the standard error to the
        ``info`` and ``error`` logging facilities respectively.

        NOTE: Using this method multiple times causes only the last loggin
              instance to receive the data.
        """
        sys.stdout = StdioOnnaStick(self.info)
        sys.stderr = StdioOnnaStick(self.error)


    def addObserver(self, observer, *args, **kwargs):
        """
        Adds the ``observer`` callable to the observers for this logger.

        The observer is only called with events matching the logger name. It is
        invoked with the provided ``*args`` and ``**kwargs``.
        """

        def observerFilter(event):
            """Filters events by name before calling the observer."""
            if event.get('name', '').startswith(self.name):
                observer(event, *args, **kwargs)

        log.addObserver(observerFilter)


    def log(self, msg, *args, **kwargs):
        """
        Proxy to the ``twisted.python.log.msg`` function which adds the config
        keys to the event dictionary and adds a timestamp to it.

        If the ``msg`` argument is a string, it will be formatted using the
        data provided in the ``*args``.

        The formatting operation used the new python formatting syntax (string
        ``format`` method) and not the old formatting operation (``%``
        operator).
        """

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
        """
        Proxy to the ``twisted.python.log.err`` function which adds the config
        keys to the event dictionary and adds a timestamp to it.
        """

        config = self.config.copy()
        config.update(kwargs)
        config['timestamp'] = datetime.now()
        log.err(_stuff, _why.format(*args), **config)


    def debug(self, msg, *args, **kwargs):
        """
        Proxy for the ``log`` method which sets the event severity to
        ``logging.DEBUG``.
        """

        kwargs['severity'] = logging.DEBUG
        self.log(msg, *args, **kwargs)


    def info(self, msg, *args, **kwargs):
        """
        Proxy for the ``log`` method which sets the event severity to
        ``logging.INFO``.
        """

        kwargs['severity'] = logging.INFO
        self.log(msg, *args, **kwargs)


    def warning(self, msg, *args, **kwargs):
        """
        Proxy for the ``log`` method which sets the event severity to
        ``logging.WARNING``.
        """

        kwargs['severity'] = logging.WARNING
        self.log(msg, *args, **kwargs)
    warn = warning


    def error(self, msg, *args, **kwargs):
        """
        Proxy for the ``log`` method which sets the event severity to
        ``logging.ERROR``.
        """

        kwargs['severity'] = logging.ERROR
        self.log(msg, *args, **kwargs)
    err = error


    def critical(self, msg, *args, **kwargs):
        """
        Proxy for the ``log`` method which sets the event severity to
        ``logging.CRITICAL``.
        """

        kwargs['severity'] = logging.CRITICAL
        self.log(msg, *args, **kwargs)
