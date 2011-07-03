"""
VURM controller daemon implementation and support classes.
"""



import os

from twisted.spread import pb
from twisted.internet import defer, utils

from vurm import logging, resources, error, cluster



class VurmController(pb.Root):
    """
    Perspective broker root for the vurm controller. This is the base instance
    which will be exposed over the network using the configured endpoint.

    TODO: Separate the implementation from the perspective broker exposed
          interface into two different classes.
    """

    def __init__(self, configuration, provisioners):
        """
        Creates a new controller with the given configuration provider and the
        given list of provisioners.

        The configuration parameter has to be a compatible with the
        ``ConfigParser.RawConfigParser`` interface.

        Each provisioner has to implement the
        vurm.resources.IResourceProvisioner interface. All passed objects will
        be adapted to the interface if they don't provide it.
        """

        self.config = configuration

        self.provisioners = []
        for prov in provisioners:
            self.provisioners.append(resources.IResourceProvisioner(prov))

        self.clusters = {}

        self.log = logging.Logger(__name__, system='vurmctld')


    @defer.inlineCallbacks
    def updateSlurmConfig(self, add='', remove='', notify=True):
        """
        Updates the SLURM configuration by adding or removing the given values.

        At least one parameter (between ``add`` and ``remove``) has to be
        defined or ``TypeError`` will be raised.

        If the ``notify`` parameter is ``True`` (the default), then the SLURM
        daemon is reconfigured by invoking the shell command defined by the
        ``reconfigure`` option of the configuration provider.

        Returns a deferred which callsback as soon as the data has been written
        or the SLURM controller was reconfigured (if notification is
        requested).

        If the SLURM controller daemon reconfiguration fails, an
        ``error.ReconfigurationError`` exception is raised.
        """

        if not add and not remove:
            raise TypeError('Provide a value to add or one to remove')

        # Marked as not covered because of bug #128:
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
                raise error.ReconfigurationError('Local slurm instance could' \
                        ' not be reconfigured (return code: {0})'.format(res))


    @defer.inlineCallbacks
    def remote_destroyVirtualCluster(self, clusterName):
        """
        Destroys the virtual cluster named by ``clusterName`` parameter.

        Raises ``error.InvalidClusterName`` if no cluster with such name is
        found or error.ReconfigurationError if the SLURM controller daemon
        could not be reconfigured.

        Returns a deferred which fires as soon as the cluster is destroyed.
        """

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
            yield self.updateSlurmConfig(
                    remove=virtualCluster.getConfigEntry())
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
        """
        Creates a new virtual cluster with ``size`` nodes. If there are not
        enough resources, the cluster is still created if at least ``minSize``
        nodes can be allocated (``minSize`` defaults to ``size``).

        The nodes are taken from the first provisioner in the list passed at
        construction time. If it can't fulfill the request completely, the
        remaining nodes are taken from the next provisioner and so on.

        Returns the name of the newly created virtual cluster. This name can
        be used as the value of the ``--partition`` argument when executing the
        ``srun`` command to submit jobs to SLURM.

        Raises ``error.InsufficientResourcesException`` if, after having
        requested nodes to all provisioners, the total number of nodes does
        not meet the ``minSize`` requirement.

        Raises ``error.ReconfigurationError`` if the cluster configuration
        could not be applied correctly to the running SLURM controller.
        """

        if minSize is None:
            minSize = size

        self.log.info('Got a new virtual cluster request for {0} nodes ' \
                '(minimum: {1})', size, minSize)

        nodes = []

        # Marked as not covered because of bug #122:
        # https://bitbucket.org/ned/coveragepy/issue/122/
        for provisioner in self.provisioners:
            count = size - len(nodes)

            for node in provisioner.getNodes(count):
                nodes.append(node.addCallback(resources.INode))

            got = len(nodes) - size + count
            self.log.debug('Got {0} nodes from {1}', got, provisioner)

            if len(nodes) == size:
                break
        else:
            if len(nodes) < minSize:
                msg = 'Not enough resources to satisfy request ' \
                        '({0}/{1})'.format(len(nodes), minSize)

                self.log.error(msg)

                for node in nodes:
                    node.addCallback(lambda n: n.release())

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
            yield self.updateSlurmConfig(
                    remove=virtualCluster.getConfigEntry(), notify=False)

            self.log.debug('Virtual cluster shutdown complete, raising to ' \
                    'caller')
            raise

        # Spawn slurm daemons
        yield virtualCluster.spawnNodes()

        self.log.info('Virtual cluster creation complete, returning to caller')

        # Return cluster to the caller
        defer.returnValue(virtualCluster.name)
