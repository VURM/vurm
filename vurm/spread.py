
import re
import functools
import itertools

from twisted.internet import defer, endpoints, protocol



class InstanceProtocolFactory(protocol.ServerFactory):

    def __init__(self, protocol, instance):
        self.protocol = protocol
        self.instance = instance


    def buildProtocol(self, addr):
        p = self.protocol()
        p.instance = self.instance

        return p



class ProtocolUpdater(protocol.ReconnectingClientFactory):

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.protocolInstance = None
        self.protocolRequests = []


    def doStart(self):
        self.protocolInstance = None


    def clientConnectionLost(self, connector, unused_reason):
        self.protocolInstance = None
        protocol.ReconnectingClientFactory.clientConnectionLost(self,
                connector, unused_reason)


    def getConnection(self):
        if self.protocolInstance:
            return defer.succeed(self.protocolInstance)
        else:
            self.protocolRequests.append(defer.Deferred())
            return self.protocolRequests[-1]


    def buildProtocol(self, addr):
        p = protocol.ReconnectingClientFactory.buildProtocol(self, addr)

        def connectionMadeCallback(factory, protocol):
            func = protocol.connectionMade

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                factory.gotConnection(protocol)
                return result
            return wrapper
        p.connectionMade = connectionMadeCallback(self, p)

        return p


    def gotConnection(self, protocol):
        self.resetDelay()
        self.protocolInstance = protocol

        requests, self.protocolRequests = self.protocolRequests, []

        for request in requests:
            request.callback(protocol)



class ReconnectingConnectionsPool(object):

    def __init__(self, reactor, protocol, endpoints):
        self.reactor = reactor
        self.protocol = protocol
        self.endpoints = {}
        self.factories = {}

        for endpoint in endpoints:
            self.endpoints.update(self.parseEndpoint(endpoint))

        self.endpointsRoundRobin = itertools.cycle(self.endpoints.keys())


    def parseEndpoint(self, endpoint):
        match = re.match(r'(.*?host=[a-zA-Z0-9_\.-]+)\[(\d+)-(\d+)\](.*)$',
                endpoint)

        if match is None:
            client = endpoints.clientFromString(self.reactor, endpoint)
            return {endpoint: client}

        flattenedEndpoints = {}

        prefix, start, end, suffix = match.groups()

        for i in range(int(start), int(end) + 1):
            endpoint = '{0}{1:0{3}d}{2}'.format(prefix, i, suffix, len(start))
            client = endpoints.clientFromString(self.reactor, endpoint)
            flattenedEndpoints[endpoint] = client

        return flattenedEndpoints


    def stop(self):
        for factory in self.factories.itervalues():
            factory.stopTrying()
            if factory.protocolInstance:
                factory.protocolInstance.transport.loseConnection()


    def start(self):
        assert not self.factories

        for endpoint, client in self.endpoints.iteritems():
            factory = ProtocolUpdater(client)
            factory.protocol = self.protocol
            self.factories[endpoint] = factory
            self.reactor.connectTCP(client._host, client._port, factory)


    def getNextConnection(self):
        return self.factories[next(self.endpointsRoundRobin)].getConnection()
