"""
Runs the vurm controller daemon.
"""



import os
import sys

from twisted.internet import reactor, endpoints

from vurm import logging, settings, controller, spread
from vurm.provisioners import remotevirt  # , multilocal



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

    # Build controller
    ctld = controller.VurmController(config, [
        remotevirt.Provisioner(reactor, config),
        #multilocal.Provisioner(reactor, config),
    ])

    # Publish daemon
    factory = spread.InstanceProtocolFactory(controller.VurmControllerProtocol,
            ctld)

    endpoint = config.get('vurmctld', 'endpoint')
    endpoint = endpoints.serverFromString(reactor, endpoint)

    endpoint.listen(factory)

    reactor.run()

    # TODO: Return the correct exit code



if __name__ == '__main__':
    sys.exit(main())
