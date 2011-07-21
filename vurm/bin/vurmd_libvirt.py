import argparse
import sys
import os

from twisted.internet import reactor, endpoints
from twisted.python import filepath

from vurm import settings, logging, spread
from vurm.provisioners.remotevirt import remote



def main():
    """
    Main program entry point.

    TODO: Implement an argument parser
    """
    parser = argparse.ArgumentParser(description='VURM libvirt helper daemon.')
    parser.add_argument('-c', '--config', type=filepath.FilePath, 
            # action='append', 
            help='Configuration file')
    args = parser.parse_args()

    # Read configuration file
    config = settings.loadConfig(args.config)

    debug = config.getboolean('vurm', 'debug')

    # Configure logging
    # TODO: Log to the file defined in the config file
    loglevel = 0 if debug else 20
    log = logging.Logger()
    log.addObserver(logging.printFormatted, sys.stdout, severity=loglevel)
    log.captureStdout()

    # Build libvirt daemon
    domainManager = remote.DomainManager(reactor, config)

    # Publish daemon
    factory = spread.InstanceProtocolFactory(remote.DomainManagerProtocol,
            domainManager)

    endpoint = config.get('vurmd-libvirt', 'endpoint')
    endpoint = endpoints.serverFromString(reactor, endpoint)

    endpoint.listen(factory)

    reactor.run()

    # TODO: Return the correct exit code



if __name__ == '__main__':
    sys.exit(main())
