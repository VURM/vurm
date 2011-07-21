"""
Releases an already existing virtual cluster and all the related resources.
"""



import argparse
import sys

from twisted.protocols import amp
from twisted.internet import reactor, endpoints, protocol
from twisted.python import filepath

from vurm import commands, settings



def main():
    """
    Main program entry point.

    TODO: Implement an argument parser
    """

    parser = argparse.ArgumentParser(description='VURM libvirt helper daemon.')
    parser.add_argument('-c', '--config', type=filepath.FilePath, 
            # action='append', 
            help='Configuration file')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true',
            help='Release all virtual clusters')
    group.add_argument('name', metavar='cluster-name', nargs='?',
            help='Name of the virtual cluster to release')
    args = parser.parse_args()

    # Read configuration file
    config = settings.loadConfig(args.config)

    factory = protocol.ClientFactory()
    factory.protocol = amp.AMP

    # Create a new endpoint
    endpoint = endpoints.clientFromString(reactor,
            config.get('vurm-client', 'endpoint'))
    d = endpoint.connect(factory)

    def gotController(controller, clusterName, deleteAll):
        """
        Called with the remote controller reference as first argument.

        Returns a deferred which fires with the result of the
        ``destroyVirtualCluster`` operation on the remote controller.
        """
        if deleteAll:
            return controller.callRemote(commands.DestroyAllVirtualClusters)
        else:
            return controller.callRemote(commands.DestroyVirtualCluster,
                    clusterName=clusterName)
    d.addCallback(gotController, args.name, args.all)

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
