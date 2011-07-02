"""
Releases an already existing virtual cluster and all the related resources.
"""



import sys

from twisted.spread import pb
from twisted.internet import reactor, endpoints



def main():
    factory = pb.PBClientFactory()

    endpoint = endpoints.TCP4ClientEndpoint(reactor, 'localhost', 8789)
    endpoint.connect(factory)

    d = factory.getRootObject()

    def gotController(controller, clusterName):
        return controller.callRemote('destroyVirtualCluster', clusterName)
    d.addCallback(gotController, sys.argv[1])

    def gotResult(_):
        print "The virtual cluster was correctly destroyed."
    d.addCallback(gotResult)

    def gotError(failure):
        print failure.value
        print failure
    d.addErrback(gotError)

    d.addBoth(lambda _: reactor.stop())

    reactor.run()



if __name__ == '__main__':
    sys.exit(main())
