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



log = logging.Logger(__name__)



class LocalNode(protocol.ProcessProtocol):

    implements(resources.INode)

    WAITING, STARTED, TERMINATING, STOPPED = range(4)


    def __init__(self, name, executable, port, reactor):
        self.name = name
        self.port = port
        self.executable = executable
        self.reactor = reactor
        self.started = defer.Deferred()
        self.stopped = defer.Deferred()
        self.status = LocalNode.WAITING


    def isRunning(self):
        return self.status == LocalNode.STARTED


    def connectionMade(self):
        self.transport.closeStdin()
        log.info('New slurmd process started with PID {0}', self.transport.pid,
                system=self.name)
        self.started.callback(self)


    #def outReceived(self, data):
    #    log.info(data.rstrip(), system=self.name)


    #def errReceived(self, data):
    #    log.err(data.rstrip(), system=self.name)


    def processExited(self, reason):
        if self.status == LocalNode.TERMINATING:
            log.debug('Process exited normally', system=self.name)
            self.status = LocalNode.STOPPED
            self.stopped.callback(self)
        else:
            log.warn('Process quit unexpectedly', system=self.name)
            self.status = LocalNode.STOPPED
            self.stopped.errback(reason)


    def processEnded(self, reason):
        if self.status != LocalNode.STOPPED:
            log.warn("Ended {0!r}", reason, system=self.name)


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

        log.info('Spawning new slurmd process')

        self.status = LocalNode.STARTED

        args = [os.path.basename(self.executable), '-D', '-N', self.name]
        self.reactor.spawnProcess(self, self.executable, args)
        return self.started


    def getConfigurationEntry(self):
        return 'NodeName={0} NodeHostname=localhost Port={1}'.format(
                self.name, self.port)


    def release(self):
        if self.isRunning():
            return self.terminate()

        return defer.succeed()



class Provisioner(object):

    implements(resources.IResourceProvisioner)


    def __init__(self, reactor, config):
        self.reactor = reactor
        self.config = config


    def getNodes(self, count):
        nodes = []

        executable = self.config.get('multilocal', 'slurmd')

        for i in range(count):
            node = LocalNode('local-{0:03d}'.format(i), executable, 17000 + i,
                self.reactor)
            nodes.append(defer.succeed(node))

        return nodes


