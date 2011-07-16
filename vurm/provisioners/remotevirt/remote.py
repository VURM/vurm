

import os

from twisted.internet import defer, threads, utils, protocol, endpoints
from twisted.python import filepath
from twisted.protocols import basic, amp
from twisted.conch.ssh import keys

from cStringIO import StringIO

from vurm import logging, error
from vurm.provisioners.remotevirt import ssh, commands, libvirt



class IPReceiverFactory(protocol.ServerFactory):

    noisy = False

    def __init__(self, reactor, key, deferred):
        self.deferred = deferred
        self.reactor = reactor
        self.key = key


    def buildProtocol(self, addr):
        p = IPReceiver(self.key, self.deferred)
        p.factory = self
        return p



class IPReceiver(basic.LineReceiver):

    def __init__(self, key, deferred):
        self.deferred = deferred
        self.key = key


    def sendKey(self):
        self.sendLine(self.key.public().toString('OPENSSH'))
        # Callback only when the key was effectively written to the guest
        self.transport.loseConnection()
        self.factory.port.stopListening()
        self.factory.reactor.callLater(1, self.deferred.callback, self.address)


    def lineReceived(self, address):
        self.address = address
        # Give to the remote end some time to open the serial interface
        self.factory.reactor.callLater(1, self.sendKey)



class DomainManagerProtocol(amp.AMP):

    @commands.CreateDomain.responder
    def createDomain(self, description):
        d = self.instance.createDomain(description)
        return d.addCallback(lambda addr: {'hostname': addr})


    @commands.DestroyDomain.responder
    def destroyDomain(self, nodeName):
        d = self.instance.destroyDomain(nodeName)
        return d.addCallback(lambda _: {})


    @commands.SpawnSlurmDaemon.responder
    def spawnDaemon(self, nodeName, slurmConfig):
        d = self.instance.spawnDaemon(nodeName, slurmConfig)
        return d.addCallback(lambda _: {})



class DomainManager(object):
    """
    Deamon which is intended to run on a physical node and can create new
    virtual domains when remotely requested.
    """

    def __init__(self, reactor, config):
        self.log = logging.Logger(__name__, system='DomainManager')
        self.reactor = reactor
        self.config = config
        self.addresses = {}


    def getHypervisor(self):
        hypervisor = self.config.get('vurmd-libvirt', 'hypervisor')

        try:
            return libvirt.open(hypervisor)
        except libvirt.LibvirtError as e:
            if e.get_error_code() == 38:
                msg = e.get_error_message()
                self.reactor.callFromThread(self.log.critical, msg)
                raise error.ConnectError(msg)
            else:
                raise


    @defer.inlineCallbacks
    def exchangeAddressAndKey(self):
        d = defer.Deferred()
        key = keys.Key.fromFile(self.config.get('vurmd-libvirt', 'key'))

        endpoint = endpoints.TCP4ServerEndpoint(self.reactor, 0,
                interface='127.0.0.1')
        factory = IPReceiverFactory(self.reactor, key, d)
        port = yield endpoint.listen(factory)
        factory.port = port
        defer.returnValue((d, port.getHost().port))


    @defer.inlineCallbacks
    def createDomain(self, description):
        self.log.info('New virtual domain creation request received')

        config = libvirt.DomainDescription(description)
        nodeName = config.getName()

        # Make a Copy-On-Write (COW) image from the original one
        original = config.getRootImagePath()
        copy = filepath.FilePath(self.config.get('vurmd-libvirt', 'clonedir'))
        copy = copy.child('{0}.qcow2'.format(nodeName))

        self.log.info('Creating new copy-on-write image based on {0} at {1}',
                original.path, copy.path)

        cmd = self.config.get('vurmd-libvirt', 'clonebin').format(
                source=original.path, destination=copy.path)
        stdout, stderr, exitCode = yield utils.getProcessOutputAndValue('sh',
                ['-c', cmd], env=os.environ)

        if exitCode:
            self.log.error('Image creation failed, qemu-img exited with ' \
                    'status code {0} (output follows):', exitCode)
            self.log.debug('stdout: {0!r}', stdout)
            self.log.debug('stderr: {0!r}', stderr)
            defer.returnValue(None)

        config.setRootImagePath(copy)

        # Enable IP callback over serial-to-tcp connection
        addressDeferred, port = yield self.exchangeAddressAndKey()
        config.addSerialToTCPDevice('127.0.0.1', port, mode='connect')

        def createInThread(config):
            with self.getHypervisor() as conn:
                conn.createLinux(str(config), 0)
        yield threads.deferToThread(createInThread, config)

        self.log.info('Domain created, waiting for guest OS to come up')

        hostname = yield addressDeferred

        self.log.info('Got IP address {0} for domain {1}', hostname, nodeName)

        self.addresses[nodeName] = hostname

        defer.returnValue(hostname)


    @defer.inlineCallbacks
    def destroyDomain(self, nodeName):
        self.log.info('Virtual domain distruction request for {0!r} received',
                nodeName)

        if nodeName in self.addresses:
            del self.addresses[nodeName]
        else:
            self.log.debug('Domain {0!r} not found in internal registry, ' \
                    'moving on', nodeName)

        # Destroy running domain
        def destroyDomain(nodeName):
            with self.getHypervisor() as conn:
                try:
                    domain = conn.lookupByName(nodeName)
                except libvirt.LibvirtError:
                    return False
                else:
                    domain.destroy()
                    return True
        destroyed = yield threads.deferToThread(destroyDomain, nodeName)

        if destroyed:
            self.log.debug('Domain {0!r} correctly destroyed', nodeName)
        else:
            self.log.debug('Domain {0!r} not running, moving on', nodeName)

        # Remove disk image from filesystem
        image = filepath.FilePath(self.config.get('vurmd-libvirt', 'clonedir'))
        image = image.child('{0}.qcow2'.format(nodeName))

        if image.exists():
            image.remove()
            self.log.debug('Disk image for domain {0!r} removed from local ' \
                    'filesystem', nodeName)
        else:
            self.log.debug('Disk image for domain {0!r} not found, moving on',
                    nodeName)


    @defer.inlineCallbacks
    def spawnDaemon(self, nodeName, config):
        self.log.info('Spawning domain')

        hostname = self.addresses[nodeName]
        username = self.config.get('vurmd-libvirt', 'username')
        keyPath = self.config.get('vurmd-libvirt', 'key')
        key = keys.Key.fromFile(keyPath)

        self.log.debug('Connection via SSH to {0}@{1} using key from {2}',
                username, hostname, keyPath)

        creator = protocol.ClientCreator(self.reactor, ssh.ClientTransport,
                username, key)

        service = yield creator.connectTCP(hostname,
                int(self.config.get('vurmd-libvirt', 'sshport')))

        remoteSlurmConf = self.config.get('vurmd-libvirt', 'slurmconfig')
        remoteSlurmConf = filepath.FilePath(remoteSlurmConf)

        yield service.executeCommand(
                'mkdir -p {0}'.format(
                        remoteSlurmConf.parent().path))

        yield service.transferFile(StringIO(config), remoteSlurmConf)

        yield service.executeCommand(
                self.config.get('vurmd-libvirt', 'slurmd').format(
                        nodeName=nodeName))

        yield service.disconnect()
