
import ConfigParser
import getpass

from lxml import etree

from twisted.trial import unittest
from twisted.internet import reactor, protocol, defer
from twisted.protocols import basic
from twisted.python import filepath
from twisted.conch.ssh import keys

from vurm.provisioners.remotevirt import remote, libvirt
from vurm import error

from .test_ssh import TestSSHServer, PRIVATE_KEY


PUBLIC_KEY = """ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAuk1btr7Povi0g1VgmZIedhtey\
vQYvZHCXy8xMiFcTAh7Mn7TzRg2R6BVHNFEoPtU2oHQ9fwx8XNFkm9MjHcK52tHHS5ax9d7Yhi+EJ\
/DsGVbFTInxSy5y3a4Vvp8NfwysF8r/xqlryigRtZzSCsQRHfsth9SApOslqFnWFM8K1vYkPtgWl7\
DPyf1DmyueaeJZgWPV+SZUfGP6waWtYKbD8OCdGf7YKYJ6JtLW+ykBqHgE/RvVGFpvXNbYPUlNOey\
l2GBciMSUaJ1Z3vSevajiBQdKUv8HYjeaRshoGL68y8OpvHIzxB8J62fiL/MQuIrwkPtaVGx170MA\
8HtKAihBQ=="""



DOMAIN_CONFIG = """<domain>
    <name>testdomain</name>
    <devices>
        <disk type="file" device="disk">
            <driver name="qemu" type="qcow2"/>
            <source file="/base/image/path"/>
            <target dev="vda" bus="virtio"/>
        </disk>
    </devices>
</domain>"""



class AddressTestProtocol(basic.LineReceiver):

    def connectionMade(self):
        self.sendLine(self.factory.hostname)

    def lineReceived(self, line):
        self.factory.key = line



class DomainManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.cloneScript = filepath.FilePath(__file__).parent().child(
                'cloner_exec.py').path

        # Create configuration object
        self.config = ConfigParser.RawConfigParser()
        self.config.add_section('vurmd-libvirt')
        self.config.set('vurmd-libvirt', 'hypervisor', 'test:///mocked')

        self.tmpKey = filepath.FilePath(self.mktemp())
        self.config.set('vurmd-libvirt', 'key', self.tmpKey.path)

        with self.tmpKey.open('w') as fh:
            fh.write(PRIVATE_KEY)


    def test_getHypervisor(self):
        manager = remote.DomainManager(reactor, self.config)

        with manager.getHypervisor() as hypervisor:
            self.assertEquals(hypervisor.uri, 'test:///mocked')

        self.assertTrue(hypervisor.closed)


    def test_getHypervisorError(self):
        manager = remote.DomainManager(reactor, self.config)

        self.config.set('vurmd-libvirt', 'hypervisor', 'test:///error/0')
        self.assertRaises(
            libvirt.LibvirtError,
            manager.getHypervisor
        )

        self.config.set('vurmd-libvirt', 'hypervisor', 'test:///error/38')
        self.assertRaises(
            error.ConnectError,
            manager.getHypervisor
        )

    @defer.inlineCallbacks
    def test_exchangeAddressAndKey(self):
        manager = remote.DomainManager(reactor, self.config)

        d, portNumber = yield manager.exchangeAddressAndKey()

        factory = protocol.ClientFactory()
        factory.protocol = AddressTestProtocol
        factory.hostname = 'localhost'
        reactor.connectTCP('localhost', portNumber, factory)

        hostname = yield d
        self.assertEquals(hostname, 'localhost')
        self.assertEquals(factory.key, PUBLIC_KEY)


    @defer.inlineCallbacks
    def test_createDomain(self):
        # Setup fake cloning support
        self.config.set('vurmd-libvirt', 'clonedir', '/tmp/clonedir')
        self.config.set('vurmd-libvirt', 'hypervisor',
                'test:///called/testCreateDomain')

        tempCallback = filepath.FilePath(self.mktemp())
        cmd = 'python {0} callback {1} {{source}} {{destination}}'.format(
                self.cloneScript, tempCallback.path)
        self.config.set('vurmd-libvirt', 'clonebin', cmd)

        # Create manager
        manager = remote.DomainManager(reactor, self.config)
        origDesc = libvirt.DomainDescription(DOMAIN_CONFIG)

        def fakeAddressKeyExchanger():
            return defer.succeed((defer.succeed('localhost'), 1234))
        manager.exchangeAddressAndKey = fakeAddressKeyExchanger

        # Create domain
        hostname = yield manager.createDomain(etree.fromstring(DOMAIN_CONFIG))
        domainDesc = libvirt.DomainDescription(
                libvirt.libvirt.Hypervisor.descriptions['testCreateDomain'])
        with tempCallback.open() as fh:
            source, destination = fh.read().strip().splitlines()

        # Post execution checks
        self.assertEquals(hostname, 'localhost')

        self.assertEquals(source, origDesc.getRootImagePath().path)

        self.assertEquals(destination, '/tmp/clonedir/testdomain.qcow2')

        port = domainDesc.document.find('devices/serial/source').get('service')
        self.assertEquals(int(port), 1234)


    @defer.inlineCallbacks
    def test_destroyDomain(self):
        tempDir = filepath.FilePath(self.mktemp())
        tempDir.makedirs()
        self.config.set('vurmd-libvirt', 'clonedir', tempDir.path)
        manager = remote.DomainManager(reactor, self.config)

        # Inexistent
        yield manager.destroyDomain('inexistent')

        # Domain only
        manager.addresses['inexistent'] = True
        yield manager.destroyDomain('inexistent')
        self.assertNotIn('inexistent', manager.addresses)

        # Image only
        tempImage = tempDir.child('inexistent.qcow2')
        tempImage.touch()
        yield manager.destroyDomain('inexistent')
        self.assertFalse(tempImage.exists())

        # Domain only
        yield manager.destroyDomain('existent')
        self.assertTrue(libvirt.libvirt.Hypervisor.lastDomain.destroyed)

        # Connect error
        self.config.set('vurmd-libvirt', 'hypervisor', 'test:///error/38')
        yield self.failUnlessFailure(
            manager.destroyDomain('inexistent'),
            error.ConnectError
        )


    @defer.inlineCallbacks
    def test_spawnDaemon(self):
        #import sys
        #from twisted.python import log
        #log.startLogging(sys.stdout)
        key = keys.Key.fromString(PRIVATE_KEY)

        self.config.set('vurmd-libvirt', 'username', getpass.getuser())
        self.config.set('vurmd-libvirt', 'sshport', '2222')
        self.config.set('vurmd-libvirt', 'slurmconfig', '/path/to/slurmconf')
        self.config.set('vurmd-libvirt', 'slurmd', '/slurmd {nodeName}')

        manager = remote.DomainManager(reactor, self.config)
        manager.addresses['testDomain'] = 'localhost'

        key = keys.Key.fromString(PRIVATE_KEY)

        self.tmpKeys = filepath.FilePath(self.mktemp())

        with self.tmpKeys.open('w') as fh:
            fh.write(key.public().toString('OPENSSH'))

        sshServer = TestSSHServer(key, self.tmpKeys)
        sshServer.startListening(2222)

        yield manager.spawnDaemon('testDomain', 'slurmConfig')

        sshServer.stopListening()

        # Check
        self.assertEquals(len(sshServer.users), 1)
        user = sshServer.users[0]

        mkdir, start = user.executedCommands
        self.assertEquals(mkdir, 'mkdir -p /path/to')
        self.assertEquals(start, '/slurmd testDomain')

        self.assertEquals(len(user.openedFiles), 1)
        config = user.openedFiles[0]
        self.assertEquals(config.name, '/path/to/slurmconf')
        self.assertEquals(config.value, 'slurmConfig')


    @defer.inlineCallbacks
    def test_cloneFail(self):
        cloneDir = filepath.FilePath(self.mktemp())
        cloneDir.makedirs()
        self.config.set('vurmd-libvirt', 'clonedir', cloneDir.path)

        cmd = 'python {0} fail'.format(self.cloneScript)
        self.config.set('vurmd-libvirt', 'clonebin', cmd)

        manager = remote.DomainManager(reactor, self.config)

        description = etree.fromstring(DOMAIN_CONFIG)
        d = manager.createDomain(description)
        result = yield d
        self.assertNotEquals(result, None)
    test_cloneFail.todo = 'Exception raising for failed disk image clones ' \
            'is not yet implemented'
