"""
Virtual clusters abstraction classes and utilities.
"""



import string
import random

from twisted.internet import defer

from vurm import logging



CLUSTER_NAME_CHARS = list(set(string.hexdigits.lower()))
"""
The characters to use to generate the virtual cluser names. Has to be an object
supporting indexing operations.
"""


CLUSTER_NAME_LENGTH = 7
"""
The length of the generated name, excluding the prefix.
"""


CLUSTER_NAME_PREFIX = 'vc-'
"""
The string to prefix to the generated cluster names.
"""


NODE_NAME_PREFIX = 'nd-'
"""
The string to prefix to the generated cluster node names.
"""



class VirtualCluster(object):
    """
    Virtual cluster abstraction to be used by the VurmController to manage
    running clusters.
    """

    __clusterNames = set()


    @staticmethod
    def nodeNamesGenerator(clusterName):
        clusterName = clusterName[len(CLUSTER_NAME_PREFIX):]
        clusterName = '{0}{1}-{{0}}'.format(NODE_NAME_PREFIX, clusterName)

        nodeCount = 0
        while True:
            yield clusterName.format(nodeCount)
            nodeCount += 1


    @classmethod
    def generateClusterName(cls):
        """
        Generates a unique cluster name. The constants ``CLUSTER_NAME_CHARS``,
        ``CLUSTER_NAME_LENGTH`` and ``CLUSTER_NAME_PREFIX`` can be used to
        customize the name format.

        The cluster names generated by the default implementation consist of
        a 7 characters long hex ID prefixed by the 'vc-' string.
        """

        rChar = lambda: random.choice(CLUSTER_NAME_CHARS)
        rID = lambda: ''.join(rChar() for x in range(CLUSTER_NAME_LENGTH))

        while True:
            name = rID()
            if name not in cls.__clusterNames:
                cls.__clusterNames.add(name)
                break

        return CLUSTER_NAME_PREFIX + name


    def __init__(self, nodes, name=None):
        """
        Creates a new virtual cluster from the given node list. The items of
        the nodes list have to provide the vurm.resources.INode interface or
        already been adapted to it, the virtual cluster instance will NOT adapt
        them.
        """

        if name is None:
            self.name = VirtualCluster.generateClusterName()
        else:
            self.name = name

        self.nodes = nodes
        self.log = logging.Logger(__name__, system=self.name)

        self.log.info('New virtual cluster created')


    def getConfigEntry(self):
        """
        Returns the string to be added to the SLURM configuration file before
        its reconfiguration to register the virtual cluster AND the nodes as
        a SLURM partition (and the relative nodes).
        """

        nodenames = 'nd-{0}-[0-{1}]'.format(self.name[3:], len(self.nodes) - 1)

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
        """
        Spawns all nodes managed by this virtual cluster. Returns a callback
        which fires with this instance as soon as all nodes have launched their
        respective SLURM daemon.
        """

        self.log.info('Spawning slurm daemons on all nodes')

        d = defer.DeferredList([n.spawn() for n in self.nodes])
        d.addCallback(lambda _: self)
        return d


    def release(self):
        """
        Releases this virtual cluster by terminating all nodes. In the current
        implementation, this method is only a proxy for the ``terminateNodes``
        method.
        """

        self.log.info('Release request received, shutting down virtual ' \
                'cluster')

        return self.terminateNodes()


    def terminateNodes(self):
        """
        Terminates all nodes currently managed by this virtual cluster by
        calling their ``release`` method. Returns a deferred wichi fires back
        with this instance as soon as all nodes have completed the release
        process.
        """

        self.log.debug('Terminating all active nodes')

        d = defer.DeferredList([n.release() for n in self.nodes])
        d.addCallback(lambda _: self)
        return d
