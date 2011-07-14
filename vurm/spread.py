
import re
import functools

from twisted.internet import defer, endpoints, protocol
from twisted.internet.interfaces import IStreamClientEndpointStringParser
from twisted.plugin import getPlugins



class SingleInstanceAMPProtocolFactory(protocol.ServerFactory):

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
        self.endpoints = []
        self.factories = []
        self.current = 0

        for endpoint in endpoints:
            self.endpoints += self.parseEndpoint(endpoint)


    def clientFromArgs(self, args, kwargs):
        aname = args.pop(0)
        name = aname.upper()

        for plugin in getPlugins(IStreamClientEndpointStringParser):
            if plugin.prefix.upper() == name:
                return plugin.parseStreamClient(*args, **kwargs)

        if name not in endpoints._clientParsers:
            raise ValueError("Unknown endpoint type: %r" % (aname,))

        kwargs = endpoints._clientParsers[name](*args, **kwargs)

        return endpoints._endpointClientFactories[name](self.reactor, **kwargs)


    def parseEndpoint(self, endpoint):
        args, kwargs = endpoints._parse(endpoint)

        match = re.match(r'(.+)\[(\d+)-(\d+)\]$', kwargs['host'])

        if match is None:
            return [endpoints.clientFromString(self.reactor, endpoint)]

        flattenedEndpoints = []

        host, start, end = match.groups()

        for i in range(int(start), int(end) + 1):
            kwargs['host'] = '{0}{1:0{2}d}'.format(host, i, len(start))
            flattenedEndpoints.append(self.clientFromArgs(args + [], kwargs))

        return flattenedEndpoints


    def start(self):
        assert not self.factories

        for endpoint in self.endpoints:
            factory = ProtocolUpdater(endpoint)
            factory.protocol = self.protocol
            self.factories.append(factory)
            self.reactor.connectTCP(endpoint._host, endpoint._port, factory)


    def getConnection(self, endpoint):
        return self.factories[self.endpoints.index(endpoint)].getConnection()


    def getNextConnection(self):
        try:
            return self.factories[self.current].getConnection()
        except IndexError:
            self.current = 0
            return self.factories[self.current].getConnection()
        finally:
            self.current += 1
