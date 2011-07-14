"""
Creates a new virtual cluster and feeds it to SLURM.
"""



import sys

from twisted.protocols import amp
from twisted.internet import reactor, endpoints, protocol

from vurm import commands



def main():
    """
    Main program entry point.

    TODO: Implement an argument parser
    """

    factory = protocol.ClientFactory()
    factory.protocol = amp.AMP

    # Create a new endpoint
    # TODO: Load this from the configuration
    endpoint = endpoints.TCP4ClientEndpoint(reactor, 'localhost', 8789)
    d = endpoint.connect(factory)

    def gotController(controller, numNodes, minNumNodes=None):
        """
        Called with the remote controller reference as first argument.

        Returns a deferred which fires with the result of the
        ``createVirtualCluster`` operation on the remote controller.
        """
        kwargs = {'size': numNodes}

        if minNumNodes:
            kwargs['minSize'] = minNumNodes

        return controller.callRemote(commands.CreateVirtualCluster, **kwargs)
    d.addCallback(gotController, int(sys.argv[1]))

    def gotResult(result):
        """
        Called when the virtual cluster creation operation succeeds with the
        name of the newly created cluster.

        Prints the result to the standard output.
        """
        print 'You can now submit jobs to the virtual cluster by using the ' \
                '--partition={0!r} option'.format(result['clusterName'])
    d.addCallback(gotResult)

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
