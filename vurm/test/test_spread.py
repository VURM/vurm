

from vurm import spread

from twisted.trial import unittest
from twisted.internet import reactor, defer, protocol



class ConnectionsPoolTestCase(unittest.TestCase):

    def setUp(self):
        pass


    def tearDown(self):
        pass


    def test_startStop(self):
        pool = spread.ReconnectingConnectionsPool(reactor, protocol.Protocol, [
            'tcp:host=localhost:port=100',
            'tcp:host=testhost[0-10]:port=100',
            'tcp:host=google.com:port=80',
        ])
        pool.start()

        d = defer.Deferred()
        reactor.callLater(1, d.callback, None)
        d.addCallback(lambda _: pool.stop())

        return d


    def test_endpointParsing(self):
        endpoints = [
            'tcp:host=testhost0:port=100',
            'tcp:host=testhost1[0-10]:port=100',
            'tcp:host=testhost2[23-28]:port=200',
            'tcp:host=testhost3[0001-0005]:port=200',
        ]

        hosts = set([
            'testhost0', 'testhost10', 'testhost11', 'testhost12',
            'testhost13', 'testhost14', 'testhost15', 'testhost16',
            'testhost17', 'testhost18', 'testhost19', 'testhost110',
            'testhost223', 'testhost224', 'testhost225', 'testhost226',
            'testhost227', 'testhost228', 'testhost30001', 'testhost30002',
            'testhost30003', 'testhost30004', 'testhost30005'
        ])

        pool = spread.ReconnectingConnectionsPool(reactor, None, endpoints)

        for endpoint in pool.endpoints.itervalues():
            hosts.remove(endpoint._host)

        self.assertFalse(hosts)
