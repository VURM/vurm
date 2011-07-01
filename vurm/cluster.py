"""
Virtual clusters abstraction classes and utilities.
"""



import string
import random

from twisted.internet import defer

from vurm import logging



CLUSTER_NAME_CHARS = list(set(string.hexdigits.lower()))

CLUSTER_NAME_LENGTH = 7

CLUSTER_NAME_PREFIX = 'vc-'



class VirtualCluster(object):

    __clusterNames = set()

    @classmethod
    def generateClusterName(cls):

        rChar = lambda: random.choice(CLUSTER_NAME_CHARS)
        rID = lambda: ''.join(rChar() for x in range(CLUSTER_NAME_LENGTH))

        while True:
            name = rID()
            if name not in cls.__clusterNames:
                cls.__clusterNames.add(name)
                break

        return CLUSTER_NAME_PREFIX + name


    def __init__(self, nodes):
        self.name = VirtualCluster.generateClusterName()
        self.nodes = nodes
        self.log = logging.Logger(__name__, system=self.name)
        
        self.log.info('New virtual cluster created')

        width = len(str(len(nodes)))

        for i, node in enumerate(nodes):
            name = 'nd-{0}-{1:0{2}d}'.format(self.name[3:], i, width)
            node.nodeName = name


    def getConfigEntry(self):
        width = len(str(len(self.nodes)))
        nodenames = 'nd-{0}-[{2:0{3}d}-{1}]'.format(self.name[3:],
                len(self.nodes)-1, 0, width)

        entries = [
            '# [{0}]'.format(self.name),
        ] + [
            n.getConfigEntry() for n in self.nodes
        ] + [
            'PartitionName={0} Nodes={1} Default=NO MaxTime=INFINITE ' \
                    'State=UP'.format(self.name, nodenames),
            '# [/{0}]'.format(self.name),
        ]

        return '\n'.join(entries) + '\n'


    def spawnNodes(self):
        self.log.info('Spawning slurm daemons on all nodes')

        d = defer.DeferredList([n.spawn() for n in self.nodes])
        d.addCallback(lambda _: self)
        return d


    def release(self):
        self.log.info('Release request received, shutting down virtual cluster')
        
        return self.terminateNodes()


    def terminateNodes(self):
        self.log.debug('Terminating all active nodes')
        
        d = defer.DeferredList([n.release() for n in self.nodes])
        d.addCallback(lambda _: self)
        return d


