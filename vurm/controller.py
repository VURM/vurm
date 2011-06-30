"""
VURM controller daemon implementation and support classes
"""



import fcntl
import string
import random

from twisted.spread import pb
from twisted.internet import defer, utils, threads

from vurm import logging, resources, error



class VirtualCluster(object):


    clusterNameLength = 7

    clusterNameChars = list(set(string.hexdigits.lower()))

    __clusterNames = set()

    @classmethod
    def generateClusterName(cls):

        def randomID():
            return 'vc-' + ''.join(random.choice(cls.clusterNameChars) for x in range(cls.clusterNameLength))

        name = randomID()

        while name in cls.__clusterNames:
            name = randomID()

        cls.__clusterNames.add(name)

        return name


    def __init__(self, nodes):
        self.name = VirtualCluster.generateClusterName()
        self.nodes = nodes

        width = len(str(len(nodes)))

        for i, node in enumerate(nodes):
            name = 'nd-{0}-{1:0{2}d}'.format(self.name[3:], i, width)
            node.nodeName = name


    def getConfigurationEntry(self):
        width = len(str(len(self.nodes)))
        nodenames = 'nd-{0}-[{2:0{3}d}-{1}]'.format(self.name[3:],
                len(self.nodes)-1, 0, width)

        entries = [
            '# [{0}]'.format(self.name),
        ] + [
            n.getConfigurationEntry() for n in self.nodes
        ] + [
            'PartitionName={0} Nodes={1} Default=NO MaxTime=INFINITE ' \
                    'State=UP'.format(self.name, nodenames),
            '# [/{0}]'.format(self.name),
        ]

        return '\n'.join(entries) + '\n'


    def spawnNodes(self):
        dl = []

        for node in self.nodes:
            dl.append(node.spawn())

        return defer.DeferredList(dl).addCallback(lambda _: self)


    def terminateNodes(self):
        d = defer.DeferredList([n.release() for n in self.nodes])
        d.addCallback(lambda _: self)
        return d



class VurmController(pb.Root):


    def __init__(self, configuration, provisioners):
        self.config = configuration
        self.provisioners = provisioners
        self.clusters = {}
        self.log = logging.Logger(__name__)


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

        self.log.debug('Got a new virtual cluster request for {0} nodes ' \
                '(minimum: {1})', size, minSize)

        nodes = []

        def adapt(node):
            return resources.INode(node)

        for provisioner in self.provisioners:
            count = size - len(nodes)

            nodes += [n.addCallback(adapt) for n in provisioner.getNodes(count)]

            got = len(nodes) - size + count
            self.log.debug('Got {0} nodes from {1}', got, provisioner)

            if len(nodes) == size:
                break
        else:
            if len(nodes) < minSize:
                self.log.error('Not enough resources to satisfy request ' \
                        '({0}/{1})', len(nodes), minSize)

                for node in nodes:
                    node.release()

                raise error.InsufficientResourcesException('MSG')

        # Wait for all nodes to be ready
        nodes = yield defer.gatherResults(nodes)

        # Create virtual cluster
        cluster = VirtualCluster(nodes)
        self.clusters[cluster.name] = cluster

        # Update slurm configuration
        yield self.updateSlurmConfig(add=cluster.getConfigurationEntry())

        # Spawn slurm daemons
        yield cluster.spawnNodes()

        # Return cluster to the caller
        defer.returnValue(cluster.name)

