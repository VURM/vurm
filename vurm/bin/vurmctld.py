"""
Runs the vurm controller daemon.
"""



import argparse
import os
import sys

from twisted.internet import reactor, endpoints
from twisted.python import filepath

from vurm import logging, settings, controller, spread
#from vurm.provisioners import multilocal
from vurm.provisioners.remotevirt import provisioner as remotevirt



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
