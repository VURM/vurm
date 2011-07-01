
import sys
import logging as py_logging
from cStringIO import StringIO

from vurm import logging

from twisted.trial import unittest
from twisted.python import failure


class LoggingTestCase(unittest.TestCase):

    def setUp(self):
        self.events = []
        self.lastEvent = None

        # Reset all observers
        self.observers = logging.log.theLogPublisher.observers
        logging.log.theLogPublisher.observers = []

        self.logger = logging.Logger()
        self.logger.addObserver(self.logObserver)

    
    def tearDown(self):
        logging.log.theLogPublisher.observers = self.observers


    def logObserver(self, event):
        self.lastEvent = event
        self.events.append(event)


    def test_stdStreamCapture(self):
        self.logger.captureStdout()

        print 'stdout'

        self.assertEquals(self.lastEvent['message'], ('stdout',))

        print >>sys.stderr, 'stderr'

        self.assertEquals(self.lastEvent['message'], ('stderr',))

        sys.stdout.writelines(['line1', 'line2'])

        self.assertEquals(self.events[-2]['message'], ('line1',))
        self.assertEquals(self.events[-1]['message'], ('line2',))


    def test_message(self):
        self.logger.log('format {0} with {1}', 5, 10)
        self.assertEquals(self.lastEvent['message'], ('format 5 with 10',))

        self.logger.log(['a', 'list', 'of', 'words'])
        self.assertEquals(self.lastEvent['message'], (['a', 'list', 'of', 'words'],))

        self.assertRaises(TypeError, self.logger.log, 1, 2)


    def test_printFormatted(self):
        """
        We don't really care about the output, run throug the function once
        with only the required (and already present) event keys to check that
        it doesn't raise an exception.
        """
        
        out = StringIO()
        logging.printFormatted({'system': '-', 'message': ''}, stream=out)
        self.assertTrue(out.getvalue())
        
        # Default severity
        out = StringIO()
        logging.printFormatted({'system': '-', 'message': ''}, stream=out,
                severity=50)
        self.assertFalse(out.getvalue())
        
        # Explicit severity
        out = StringIO()
        logging.printFormatted({'system': '-', 'message': '', 'severity': 40},
                stream=out, severity=50)
        self.assertFalse(out.getvalue())
        
        out = StringIO()
        logging.printFormatted({'system': '-', 'message': '', 'severity': 40},
                stream=out, severity=30)
        self.assertTrue(out.getvalue())


    def test_exception(self):
        try:
            raise Exception()
        except Exception as e:
            self.logger.exception(e, 'format {0} with {1}', 5, 10)

            self.assertEquals(self.lastEvent['isError'], 1)
            self.assertEquals(self.lastEvent['message'], tuple())
            self.assertEquals(self.lastEvent['why'], 'format 5 with 10',)

            self.flushLoggedErrors(Exception)


    def test_filter(self):
        loggers = {
            '': [5, 0, None],
            'a': [3, 0, None],
            'a.b': [2, 0, None],
            'a.b.c': [1, 0, None],
            'c.b': [1, 0, None],
        }

        def checkName(event, name):
            self.assertTrue(event['name'].startswith(name))
            loggers[name][1] += 1

        for name, values in loggers.iteritems():
            values[2] = logging.Logger(name)
            values[2].addObserver(checkName, name)

        for logger in loggers.values():
            logger[2].log('msg')

        for logger in loggers.values():
            self.assertEquals(logger[0], logger[1])


    def test_severity(self):
        self.logger.debug('msg')
        self.assertEquals(self.lastEvent['severity'], py_logging.DEBUG)

        self.logger.info('msg')
        self.assertEquals(self.lastEvent['severity'], py_logging.INFO)

        self.logger.warning('msg')
        self.assertEquals(self.lastEvent['severity'], py_logging.WARNING)

        self.logger.warn('msg')
        self.assertEquals(self.lastEvent['severity'], py_logging.WARNING)

        self.logger.error('msg')
        self.assertEquals(self.lastEvent['severity'], py_logging.ERROR)

        self.logger.err('msg')
        self.assertEquals(self.lastEvent['severity'], py_logging.ERROR)

        self.logger.critical('msg')
        self.assertEquals(self.lastEvent['severity'], py_logging.CRITICAL)

        self.logger.log('msg')
        self.assertFalse('severity' in self.lastEvent)

        self.logger.log('msg', severity=23)
        self.assertEquals(self.lastEvent['severity'], 23)
