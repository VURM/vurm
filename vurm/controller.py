"""
VURM controller daemon implementation and support classes
"""



import os

from twisted.spread import pb
from twisted.internet import defer, utils

from vurm import logging, resources, error, cluster



class VurmController(pb.Root):


    def __init__(self, configuration, provisioners):
        self.config = configuration
        self.provisioners = [resources.IResourceProvisioner(p) for p in provisioners]
        self.clusters = {}
        self.log = logging.Logger(__name__, system='vurmctld')


    @defer.inlineCallbacks
    def updateSlurmConfig(self, add='', remove='', notify=True):
        if not add and not remove:
            raise TypeError('Provide a value to add or one to remove')

        # Marked as not covered because of bug #122:
        # https://bitbucket.org/ned/coveragepy/issue/128/
        with open(self.config.get('vurmctld', 'slurmconfig'), 'r+') as fh:
            newConf = fh.read()
            newConf = newConf.replace(remove, '')
            newConf += add

            fh.seek(0)
            fh.truncate()

            fh.write(newConf)

        if notify:
            # Reload slurm config file
            cmd = self.config.get('vurmctld', 'reconfigure')

            res = yield utils.getProcessValue('sh', ['-c', cmd],
                    env=os.environ)

            if res:
                raise error.ReconfigurationError('Local slurm instance could ' \
                        'not be reconfigured (return code: {0})'.format(res))


    @defer.inlineCallbacks
    def remote_destroyVirtualCluster(self, clusterName):
        self.log.info('Got a virtual cluster shutdown request for {0!r}',
                clusterName)

        try:
            virtualCluster = self.clusters[clusterName]
        except KeyError:
            msg = 'No such cluster: {0!r}'.format(clusterName)

            self.log.error(msg)
            raise error.InvalidClusterName(msg)
        else:
            del self.clusters[clusterName]

        yield virtualCluster.release()

        self.log.debug('Updating SLURM configuration file and restarting ' \
                'local daemon')

        try:
            # Update slurm configuration
            yield self.updateSlurmConfig(remove=virtualCluster.getConfigEntry())
        except error.ReconfigurationError:
            # The slurm controller daemon could not be contacted, it is
            # probably not running. Let the client deal with that.

            self.log.error('Failed to reconfigure the slurm controller ' \
                    'daemon, raising to caller')

            raise
        else:
            self.log.info('Virtual cluster correctly shut down, returning ' \
                    'to caller')


    @defer.inlineCallbacks
    def remote_createVirtualCluster(self, size, minSize=None):

        if minSize is None:
            minSize = size

        self.log.info('Got a new virtual cluster request for {0} nodes ' \
                '(minimum: {1})', size, minSize)

        nodes = []

        def adapt(node):
            return resources.INode(node)

        # Marked as not covered because of bug #122:
        # https://bitbucket.org/ned/coveragepy/issue/122/
        for provisioner in self.provisioners:
            count = size - len(nodes)

            nodes += [n.addCallback(adapt) for n in provisioner.getNodes(count)]

            got = len(nodes) - size + count
            self.log.debug('Got {0} nodes from {1}', got, provisioner)

            if len(nodes) == size:
                break
        else:
            if len(nodes) < minSize:
                msg = 'Not enough resources to satisfy request ' \
                        '({0}/{1})'.format(len(nodes), minSize)
                
                self.log.error(msg)

                def release(node):
                    node.release()

                for node in nodes:
                    node.addCallback(release)

                raise error.InsufficientResourcesException(msg)

        self.log.debug('Waiting for all nodes to come up')

        # Wait for all nodes to be ready
        nodes = yield defer.gatherResults(nodes)

        # Create virtual cluster
        virtualCluster = cluster.VirtualCluster(nodes)
        self.clusters[virtualCluster.name] = virtualCluster

        self.log.debug('Updating SLURM configuration file and restarting ' \
                'local daemon')

        try:
            # Update slurm configuration
            yield self.updateSlurmConfig(add=virtualCluster.getConfigEntry())
        except error.ReconfigurationError:
            # The slurm controller daemon could not be contacted, it is
            # probably not running. Let the client deal with that, but free up
            # the resources requested to the different provisioners before.

            self.log.error('Failed to reconfigure the slurm controller ' \
                    'daemon, releasing virtual cluster')

            yield virtualCluster.release()

            # Remove the just written configuration, but without notifying the
            # controller.
            yield self.updateSlurmConfig(remove=virtualCluster.getConfigEntry(),
                    notify=False)

            self.log.debug('Virtual cluster shutdown complete, raising to ' \
                    'caller')
            raise

        # Spawn slurm daemons
        yield virtualCluster.spawnNodes()

        self.log.info('Virtual cluster creation complete, returning to caller')

        # Return cluster to the caller
        defer.returnValue(virtualCluster.name)

