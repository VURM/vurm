

import ConfigParser
import random

from twisted.trial import unittest
from twisted.python import filepath
from twisted.protocols import amp
from twisted.internet import reactor, protocol, endpoints, defer

from vurm.provisioners.remotevirt import provisioner, commands
from vurm.provisioners import remotevirt
from vurm import resources, spread



DOMAIN_CONFIG = """<domain>
	<name>This will be replaced with the unique domain name</name>
	<devices>
		<disk type="file" device="disk">
			<driver name="qemu" type="qcow2"/>
			<source file="/home/garetjax/images/debian-base.qcow2"/>
			<target dev="vda" bus="virtio"/>
		</disk>
	</devices>
</domain>"""


SLURM_CONFIG = """SlurmConfig"""



class FakeDomainManager(object):

    def __init__(self):
        self.created = 0
        self.destroyed = 0
        self.spawned = 0
        self.configs = {}


    def createDomain(self, description):
        self.created += 1
        return defer.succeed('localhost')


    def destroyDomain(self, nodeName):
        self.destroyed += 1
        return defer.succeed(None)


    def spawnDaemon(self, nodeName, slurmConfig):
        self.spawned += 1
        self.configs[nodeName] = slurmConfig
        return defer.succeed(None)



class VirtualNodeTestCase(unittest.TestCase):
    
    def test_config(self):
        node = provisioner.VirtualNode(None, None, 'node-a', 'localhost')
        config = node.getConfigEntry()
        
        self.assertEquals('NodeName=node-a NodeHostname=localhost', config)


class ProvisionerTestCase(unittest.TestCase):

    def setUp(self):
        self.ports = []
        self.provisioners = []

        # Create configuration object
        self.config = ConfigParser.RawConfigParser()
        self.config.add_section('libvirt')
        self.config.add_section('vurmctld')

        self.tmpXML = filepath.FilePath(self.mktemp())
        self.config.set('libvirt', 'domainXML', self.tmpXML.path)

        with self.tmpXML.open('w') as fh:
            fh.write(DOMAIN_CONFIG)

        self.tmpConfig = filepath.FilePath(self.mktemp())
        self.config.set('vurmctld', 'slurmconfig', self.tmpConfig.path)

        with self.tmpConfig.open('w') as fh:
            fh.write(SLURM_CONFIG)


    @defer.inlineCallbacks
    def tearDown(self):
        for prov in self.provisioners:
            yield prov.nodes.stop()

        for port in self.ports:
            yield port.stopListening()


    @defer.inlineCallbacks
    def startListening(self, manager, count=1):
        factory = spread.InstanceProtocolFactory(
                remotevirt.DomainManagerProtocol, manager)
        endpoint = endpoints.TCP4ServerEndpoint(reactor, 0)

        servers = []

        for _ in range(count):
            port = yield endpoint.listen(factory)
            self.ports.append(port)
            servers.append('tcp:host=localhost:port={0}'.format(
                    port.getHost().port))

        defer.returnValue('\n'.join(servers))


    @defer.inlineCallbacks
    def createProvisionerWithNodes(self, count=1):
        manager = FakeDomainManager()
        endpoints = yield self.startListening(manager, count)
        self.config.set('libvirt', 'nodes', endpoints)
        prov = remotevirt.Provisioner(reactor, self.config)
        self.provisioners.append(prov)
        defer.returnValue((prov, manager))


    @defer.inlineCallbacks
    def test_getNodes(self):
        prov, manager = yield self.createProvisionerWithNodes(10)
        nodes = prov.getNodes(10, iter('abcdefghijklmnop'))
        yield defer.gatherResults(nodes)

        self.assertEquals(10, manager.created)
        self.assertEquals(0, manager.spawned)
        self.assertEquals(0, manager.destroyed)


    @defer.inlineCallbacks
    def test_spawnNodes(self):
        prov, manager = yield self.createProvisionerWithNodes(10)
        nodes = prov.getNodes(10, iter('abcdefghijklmnop'))
        nodes = yield defer.gatherResults(nodes)

        yield defer.DeferredList([node.spawn() for node in nodes])

        self.assertEquals(10, manager.created)
        self.assertEquals(10, manager.spawned)
        self.assertEquals(0, manager.destroyed)


    @defer.inlineCallbacks
    def test_releaseNodes(self):
        prov, manager = yield self.createProvisionerWithNodes(10)
        nodes = prov.getNodes(10, iter('abcdefghijklmnop'))
        nodes = yield defer.gatherResults(nodes)

        yield defer.DeferredList([node.release() for node in nodes])

        self.assertEquals(10, manager.created)
        self.assertEquals(0, manager.spawned)
        self.assertEquals(10, manager.destroyed)



class LocalNodeTestCase(unittest.TestCase):
    pass
