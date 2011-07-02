"""
Classes and utilities to provide a resource provisioner which simply spawns
multiple `slurmd` processes on the local machine by using SLURM's support for
multiple daemons.

This provisioner is only supported by SLURM if it was compiled and configured
to support multiple daemons according to the user manual:

    https://computing.llnl.gov/linux/slurm/programmer_guide.html#multiple_slurmd_support

"""



import os
import signal

from zope.interface import implements

from twisted.internet import protocol, defer

from vurm import resources, logging



class LocalNode(protocol.ProcessProtocol, object):

    implements(resources.INode)

    WAITING, STARTED, TERMINATING, STOPPED = range(4)


    def __init__(self, slurmd, port, reactor):
        self._nodeName = None
        self.port = port
        self.hostname = 'localhost'

        self.log = logging.Logger(__name__)
        self.slurmd = slurmd
        self.reactor = reactor
        self.started = defer.Deferred()
        self.stopped = defer.Deferred()
        self.status = LocalNode.WAITING


    @property
    def nodeName(self):
        return self._nodeName

    @nodeName.setter
    def nodeName(self, value):
        self.log.config['system'] = value
        self._nodeName = value


    def isRunning(self):
        return self.status == LocalNode.STARTED


    def connectionMade(self):
        self.transport.closeStdin()
        self.log.info('New slurmd process started with PID {0}',
                self.transport.pid)
        self.started.callback(self)


    def outReceived(self, data):
        self.log.debug(data.rstrip())


    def errReceived(self, data):
        self.log.debug(data.rstrip())


    def processEnded(self, reason):
        if self.status == LocalNode.TERMINATING:
            self.log.debug('Process exited normally ({0!r})', reason)
            self.status = LocalNode.STOPPED
            self.stopped.callback(self)
        else:
            self.log.warn('Process quit unexpectedly ({0!r})', reason)
            self.status = LocalNode.STOPPED
            self.stopped.errback(reason)


    def terminate(self):
        if self.status != LocalNode.STARTED:
            raise RuntimeError('Can only terminate a node in the RUNNING status')

        self.status = LocalNode.TERMINATING
        os.kill(self.transport.pid, signal.SIGTERM)

        return self.stopped


    def spawn(self):
        """
        Spawns a new slurmd process locally and returns a deferred which fires
        as soon as the process was launched.
        """
        if self.status != LocalNode.WAITING:
            raise RuntimeError('Can only spawn a node in the WAITING status')

        self.log.debug('Spawning new slurmd process')

        self.status = LocalNode.STARTED

        formatArgs = {
            'nodeName': self.nodeName,
            'hostname': self.hostname,
            'port': self.port,
        }

        args = ['sh', '-c', self.slurmd.format(**formatArgs)]
        self.reactor.spawnProcess(self, 'sh', args)
        return self.started


    def getConfigEntry(self):
        return 'NodeName={self.nodeName} NodeHostname={self.hostname} ' \
                'Port={self.port}'.format(self=self)


    def release(self):
        if self.isRunning():
            return self.terminate()

        return defer.succeed(self)



class Provisioner(object):

    implements(resources.IResourceProvisioner)

    __currentPort = None


    def getNextPort(self):
        cls = self.__class__

        if cls.__currentPort is None:
            cls.__currentPort = self.basePort
        else:
            cls.__currentPort += 1

        return cls.__currentPort


    def __init__(self, reactor, config):
        self.reactor = reactor
        self.config = config
        self.basePort = config.getint('multilocal', 'baseport')


    def getNodes(self, count):
        nodes = []

        slurmd = self.config.get('multilocal', 'slurmd')

        for i in range(count):
            node = LocalNode(slurmd, self.getNextPort(), self.reactor)
            nodes.append(defer.succeed(node))

        return nodes


