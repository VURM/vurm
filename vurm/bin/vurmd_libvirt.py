import sys
import os

from twisted.internet import reactor, endpoints

from vurm import settings, logging, spread
from vurm.provisioners.remotevirt import remote



def main():
    """
    Main program entry point.

    TODO: Implement an argument parser
    """

    # TODO: for testing only, remove the following line
    settings.DEFAULT_FILES.append(os.path.join(os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))), 'tests',
            'config.ini'))

    # Read configuration file
    config = settings.loadConfig()

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
