"""
Classes and utilities to provide a resource provisioner which simply spawns
multiple ``slurmd`` processes on the local machine by using SLURM's support for
multiple daemons.

This provisioner is only supported by SLURM if it was compiled and configured
to support multiple daemons according to the user manual:

    https://computing.llnl.gov/linux/slurm/programmer_guide.html#multiple_slurmd_support

"""



from zope.interface import implements

from twisted.internet import protocol, defer

from vurm import resources, logging



class LocalNode(object):
    """
    A class implementing the ``INode`` interface which runs a ``slurmd``
    process locally using SLURM's multiple daemons support.
    """

    implements(resources.INode)


    def __init__(self, nodeName, slurmd, port, reactor):
        """
        Creates a new nodes which spawns a slurm daemon using the command
        contained in the ``slurmd`` parameter on the given port.

        The ``reactor`` parameter shall be a valid Twisted reactor instance and
        will be used to spawn the process.
        """
        self.nodeName = nodeName
        self.port = port
        self.hostname = 'localhost'

        self.log = logging.Logger(__name__, system=self.nodeName)
        self.slurmd = slurmd
        self.reactor = reactor
        self.started = defer.Deferred()
        self.stopped = defer.Deferred()
        self.process = LocalNode.SlurmdProtocol(self)


    def isRunning(self):
        """
        Returns ``True`` if the process bound to this node instance was already
        spawned and not yet terminated.
        """

        return self.process.status == LocalNode.SlurmdProtocol.STARTED


    def terminate(self):
        """
        Terminates the process bound to this node instance.

        Raises a ``RuntimeError`` if the process is not currently running.

        Returns a deferred which fires back with the node instance as soon as
        the process exits.
        """

        if self.process.status != LocalNode.SlurmdProtocol.STARTED:
            raise RuntimeError('Can only terminate a node in the RUNNING ' \
                    'status')

        self.process.status = LocalNode.SlurmdProtocol.TERMINATING
        self.process.transport.signalProcess('KILL')

        return self.stopped


    def spawn(self):
        """
        Spawns a new slurmd process locally and returns a deferred which fires
        as soon as the process was launched.
        """

        if self.process.status != LocalNode.SlurmdProtocol.WAITING:
            raise RuntimeError('Can only spawn a node in the WAITING status')

        self.log.debug('Spawning new slurmd process')

        self.process.status = LocalNode.SlurmdProtocol.STARTED

        formatArgs = {
            'nodeName': self.nodeName,
            'hostname': self.hostname,
            'port': self.port,
        }

        args = ['sh', '-c', self.slurmd.format(**formatArgs)]
        self.reactor.spawnProcess(self.process, 'sh', args)
        return self.started


    def getConfigEntry(self):
        """
        Returns the configuration entry to be added to the SLURM configuration
        file for this node to be recognized as such by the SLURM controller.
        """

        return 'NodeName={self.nodeName} NodeHostname={self.hostname} ' \
                'Port={self.port}'.format(self=self)


    def release(self):
        """
        Calls ``terminate`` if the node is running and does nothing otherwise.

        Returns a deferred which fires back with the node itself as soon as
        the process exits (or striaght away if the process was not running).
        """

        if self.isRunning():
            return self.terminate()

        return defer.succeed(self)


    class SlurmdProtocol(protocol.ProcessProtocol):
        """
        Process protocol to handle the INode lifecycle of the bound process.
        """

        WAITING, STARTED, TERMINATING, STOPPED = range(4)


        def __init__(self, node):
            """
            Creates a new instance bound to the given ``LocalNode`` isntance.
            """
            self.node = node
            self.status = LocalNode.SlurmdProtocol.WAITING

        def connectionMade(self):
            """
            Called when the process spawns. Closes the standard input and
            fires the ``started`` callback on the bound node instance.
            """
            self.transport.closeStdin()
            self.node.log.info('New slurmd process started with PID {0}',
                    self.transport.pid)
            self.node.started.callback(self.node)


        def outReceived(self, data):
            """
            Redirects the process stdout stream to the logger with ``DEBUG``
            severity.
            """
            self.node.log.debug(data.rstrip())


        def errReceived(self, data):
            """
            Redirects the process stderr stream to the logger with ``DEBUG``
            severity.
            """
            self.node.log.debug(data.rstrip())


        def processEnded(self, reason):
            """
            Called when the process exits. If the node's status was set to
            ``TERMINATING``, fires the ``stopped`` callback on the bound node
            instance, else fire the ``stopped`` errback.
            """
            if self.status == LocalNode.SlurmdProtocol.TERMINATING:
                self.node.log.debug('Process exited normally ({0!r})', reason)
                self.status = LocalNode.SlurmdProtocol.STOPPED
                self.node.stopped.callback(self.node)
            else:
                self.node.log.warn('Process quit unexpectedly ({0!r})', reason)
                self.status = LocalNode.SlurmdProtocol.STOPPED
                self.node.stopped.errback(reason)



class Provisioner(object):
    """
    A class implementing the ``IResourceProvisioner`` interface to provide
    nodes as local ``slurmd`` processes.

    This provisioner has no resource limit and rescheduling capabilities.
    """

    implements(resources.IResourceProvisioner)

    __currentPort = None


    def __init__(self, reactor, config):
        """
        Creates a new ``Provisioner`` instance with the given configuration and
        Twisted reactor.
        """

        self.reactor = reactor
        self.config = config
        self.basePort = config.getint('multilocal', 'baseport')


    def getNextPort(self):
        """
        Returns the next unique port among all provisioners of this type,
        starting at the base port defined in the configuration file and
        incrementing its value at each request.
        """

        if Provisioner.__currentPort is None:
            Provisioner.__currentPort = self.basePort
        else:
            Provisioner.__currentPort += 1

        return Provisioner.__currentPort


    def getNodes(self, count, names, **kwargs):
        """
        Returns ``count`` deferreds with their callback already called with a
        correctly configured ``LocalNode`` instance ready to be spawned.

        As there are no resource limits on this provider, this method always
        succeeds.
        """

        nodes = []

        slurmd = self.config.get('multilocal', 'slurmd')

        for _ in range(count):
            node = LocalNode(next(names), slurmd, self.getNextPort(),
                    self.reactor)
            nodes.append(defer.succeed(node))

        return nodes
