"""
Creates a new virtual cluster and feeds it to SLURM.
"""



import sys

from twisted.spread import pb
from twisted.internet import reactor, endpoints



def main():
    """
    Main program entry point.

    TODO: Implement an argument parser
    """

    factory = pb.PBClientFactory()

    # Create a new endpoint
    # TODO: Load this from the configuration
    endpoint = endpoints.TCP4ClientEndpoint(reactor, 'localhost', 8789)
    endpoint.connect(factory)

    d = factory.getRootObject()


    def gotController(controller, numNodes, minNumNodes=None):
        """
        Called with the remote controller reference as first argument.

        Returns a deferred which fires with the result of the
        ``createVirtualCluster`` operation on the remote controller.
        """
        return controller.callRemote('createVirtualCluster', numNodes,
                minNumNodes)
    d.addCallback(gotController, int(sys.argv[1]))


    def gotName(name):
        """
        Called when the virtual cluster creation operation succeeds with the
        name of the newly created cluster.

        Prints the result to the standard output.
        """
        print "You can now submit jobs to the virtual cluster by using the ' \
                '--partition={0!r} option".format(name)
    d.addCallback(gotName)


    def gotError(failure):
        """
        Called when the virtual cluster creation operation fails.

        Prints the error to the standard output.
        """
        print failure.value
        print failure
    d.addErrback(gotError)


    # Make sure to exit once done
    d.addBoth(lambda _: reactor.stop())

    # Run the reactor
    reactor.run()

    # TODO: Return the correct exit code



if __name__ == '__main__':
    sys.exit(main())
