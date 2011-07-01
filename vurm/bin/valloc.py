"""
Creates a new virtual cluster and feeds it to SLURM.
"""



import sys

from twisted.spread import pb
from twisted.internet import reactor, endpoints
from twisted.python import log



def main():
    factory = pb.PBClientFactory()

    endpoint = endpoints.TCP4ClientEndpoint(reactor, 'localhost', 8789)
    endpoint.connect(factory)

    d = factory.getRootObject()

    def gotController(controller, numNodes, minNumNodes=None):
        return controller.callRemote('createVirtualCluster', numNodes, minNumNodes)
    d.addCallback(gotController, int(sys.argv[1]))

    def gotName(name):
        print "You can now submit jobs to the virtual cluster by using the --partition={0!r} option".format(name)
    d.addCallback(gotName)

    def gotError(failure):
        print failure.value
        print failure
    d.addErrback(gotError)

    d.addBoth(lambda _: reactor.stop())

    reactor.run()



if __name__ == '__main__':
    sys.exit(main())