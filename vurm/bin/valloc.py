"""
Creates a new virtual cluster and feeds it to SLURM.
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
    parser.add_argument('minsize', type=int, help='Minimum acceptable virtual cluster size', nargs='?', default=0)
    parser.add_argument('size', type=int, help='Desired virtual cluster size')
    args = parser.parse_args()

    # Read configuration file
    config = settings.loadConfig(args.config)

    factory = protocol.ClientFactory()
    factory.protocol = amp.AMP

    # Create a new endpoint
    endpoint = endpoints.clientFromString(reactor,
            config.get('vurm-client', 'endpoint'))
    d = endpoint.connect(factory)

    def gotController(controller, numNodes, minNumNodes):
        """
        Called with the remote controller reference as first argument.

        Returns a deferred which fires with the result of the
        ``createVirtualCluster`` operation on the remote controller.
        """
        kwargs = {'size': numNodes}

        if minNumNodes > 0:
            kwargs['minSize'] = minNumNodes

        return controller.callRemote(commands.CreateVirtualCluster, **kwargs)
    d.addCallback(gotController, args.size, args.minsize)

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
