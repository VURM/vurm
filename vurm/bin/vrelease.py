"""
Releases an already existing virtual cluster and all the related resources.
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

    def gotController(controller, clusterName):
        """
        Called with the remote controller reference as first argument.

        Returns a deferred which fires with the result of the
        ``destroyVirtualCluster`` operation on the remote controller.
        """
        return controller.callRemote(commands.DestroyVirtualCluster,
                clusterName=clusterName)
    d.addCallback(gotController, sys.argv[1])

    def gotResult(_):
        """
        Called when the virtual cluster destruction operation succeeds.

        Prints a confirmation message to the standard output.
        """
        print "The virtual cluster was correctly destroyed."
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
