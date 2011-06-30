"""
Runs the vurm controller daemon.
"""



import sys

from twisted.spread import pb
from twisted.internet import reactor, endpoints

from vurm import logging, settings, controller
from vurm.provisioners import multilocal



def main():
    # Read configuration file
    config = settings.loadConfig()

    debug = config.getboolean('vurmctld', 'debug')

    # Configure logging
    # TODO: Log to the file defined in the config file
    log = logging.Logger()
    log.captureStdout()
    log.addObserver(log.printFormatted, severity=0 if debug else 20)

    # Build controller
    ctld = controller.VurmController(config, [
        multilocal.Provisioner(reactor, config),
    ])

    # Publish daemon
    factory = pb.PBServerFactory(ctld, unsafeTracebacks=debug)

    endpoint = config.get('vurmctld', 'endpoint')
    endpoint = endpoints.serverFromString(reactor, endpoint)

    endpoint.listen(factory)

    reactor.run()



if __name__ == '__main__':
    sys.exit(main())



#class ImageCollector(pb.Referenceable):
#
#    def __init__(self, fd, closeOnPagingEnd=True):
#        self.fd = fd
#        self.closeOnPagingEnd = closeOnPagingEnd
#
#
#    def remote_gotPage(self, page):
#        self.fd.write(page)
#
#
#    def remote_endedPaging(self):
#        if self.closeOnPagingEnd:
#            self.fd.close()
#
#
#class VurmController(pb.Root):
#
#
#    def __init__(self, provisioners):
#        self.provisioners = provisioners
#
#
#    def remote_createImage(self, imageId):
#        return ImageCollector(open(ROOT + imageId, 'w'))
#
#
#    def remote_createVirtualCluster(self, size):
#        return VirtualCluster(nodes)
#
#
#class VirtualCluster(pb.Referenceable):
#
#    def __init__(self, size, image):
#        self.size = size
#        self.image = image



#class ClusterProvisioner(pb.Root):
#
#    implements(IResourceProvisioner)
#
#    def __init__(self):
#        self.nodes = {}
#
#
#    def getMachines(self, count, image):
#        raise NotImplementedError()
#
#
#    def remote_heartbeat(self, name):
#        log.info('Node {0} still alive', name)
#        for node in self.nodes:
#            node.callRemote('shutdown')
#
#
#    def remote_registerNode(self, name, node):
#        log.info('Node {0} registered', name)
#        self.nodes[nodeName] = node


#def createImage(controller):
#    d = controller.callRemote('createImage', 'image-id')
#    return d
#d.addCallback(createImage)
#
#def sendImage(ctl):
#    d = defer.Deferred()
#    util.FilePager(ctl, open(FILE), callback=lambda: d.callback(None))
#    return d
#d.addCallback(sendImage)
#
#def stop():
#    print "Stopping"
#    reactor.stop()
#
#def done(_):
#    reactor.callLater(1, stop)
#d.addCallback(done)