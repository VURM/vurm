"""
Runs the vurm controller daemon.
"""



import sys
import fcntl

from twisted.spread import pb
from twisted.internet import reactor, endpoints, defer, utils, threads

from vurm import logging, resources, settings
from vurm.provisioners import multilocal


log = logging.Logger()
log.captureStdout()
log.addObserver(log.printFormatted)



class RemoteVurmException(pb.Error):
    pass



class InsufficientResourcesException(RemoteVurmException):
    pass



class VirtualCluster(pb.Referenceable):

    def __init__(self, name, nodes):
        self.name = name
        self.nodes = nodes


    def getConfigurationEntry(self):
        entries = [
            '# $VC: {0}$ start'.format(self.name),
        ] + [
            n.getConfigurationEntry() for n in self.nodes
        ] + [
            '# $VC: {0}$ end'.format(self.name),
        ]

        return '\n'.join(entries)


    def spawnNodes(self):
        d = defer.DeferredList([n.spawn() for n in self.nodes])
        d.addCallback(lambda _: self)
        return d


    def terminateNodes(self):
        d = defer.DeferredList([n.release() for n in self.nodes])
        d.addCallback(lambda _: self)
        return d



class VurmController(pb.Root):


    def __init__(self, configuration, provisioners):
        self.config = configuration
        self.provisioners = provisioners
        self.clusters = {}
        self._clusterCount = 0


    @defer.inlineCallbacks
    def updateSlurmConfig(self, add='', remove='', notify=True):
        if not add and not remove:
            raise ValueError('Provide a value to add or one to remove')

        with open(self.config.get('vurmctld', 'slurmconfig'), 'r+') as fh:
            # Try to do our best to avoid racing conditions
            # This may block... not good for twisted, defer it to a thread
            yield threads.deferToThread(fcntl.lockf, fh, fcntl.LOCK_EX)

            newConf = fh.read()
            newConf = newConf.replace(remove, '')
            newConf += add

            fh.seek(0)
            fh.truncate()

            fh.write(newConf)

        if notify:
            # Reload slurm config file
            yield utils.getProcessValue('/usr/local/bin/scontrol',
                    ['reconfigure'])


    @defer.inlineCallbacks
    def remote_destroyVirtualCluster(self, clusterName):
        cluster = self.clusters[clusterName]
        del self.clusters[clusterName]

        yield cluster.terminateNodes()

        # Update slurm configuration
        yield self.updateSlurmConfig(remove=cluster.getConfigurationEntry())


    @defer.inlineCallbacks
    def remote_createVirtualCluster(self, size, minSize=None):

        if minSize is None:
            minSize = size

        log.debug('Got a new virtual cluster request for {0} nodes ' \
                '(minimum: {1})', size, minSize)

        nodes = []

        def adapt(node):
            return resources.INode(node)

        for provisioner in self.provisioners:
            count = size - len(nodes)

            nodes += [n.addCallback(adapt) for n in provisioner.getNodes(count)]

            got = len(nodes) - size + count
            log.debug('Got {0} nodes from {1}', got, provisioner)

            if len(nodes) == size:
                break
        else:
            if len(nodes) < minSize:
                log.error('Not enough resources to satisfy request ({0}/{1})',
                        len(nodes), minSize)

                for node in nodes:
                    node.release()

                raise InsufficientResourcesException('MSG')

        # Wait for all nodes to be ready
        nodes = yield defer.gatherResults(nodes)

        # Create virtual cluster
        name = 'virtual-cluster-{0:03d}'.format(self._clusterCount)
        self._clusterCount += 1
        cluster = VirtualCluster(name, nodes)
        self.clusters[name] = cluster

        # Update slurm configuration
        yield self.updateSlurmConfig(add=cluster.getConfigurationEntry())

        # Spawn slurm daemons
        yield cluster.spawnNodes()

        # Return cluster to the caller
        defer.returnValue(cluster.name)



def main():
    # Read configuration file
    config = settings.loadConfig()

    controller = VurmController(config, [
        multilocal.Provisioner(reactor, config),
    ])

    factory = pb.PBServerFactory(controller, unsafeTracebacks=True)

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