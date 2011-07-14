
from lxml import etree

from twisted.internet import defer
from twisted.protocols import amp

from zope.interface import implements

from vurm import resources, logging, spread
from vurm.provisioners.remotevirt import commands



class VirtualNode(object):

    implements(resources.INode)


    def __init__(self, provisioner, connectionProvider, nodeName, hostname):
        self.connectionProvider = connectionProvider
        self.provisioner = provisioner
        self.nodeName = nodeName
        self.hostname = hostname
        self.port = 6818  # Default SlurmdPort setting


    @defer.inlineCallbacks
    def spawn(self):
        configPath = self.provisioner.config.get('vurmctld', 'slurmconfig')
        with open(configPath) as fh:
            config = fh.read()

        remote = yield self.connectionProvider.getConnection()
        yield remote.callRemote(commands.SpawnSlurmDaemon,
                nodeName=self.nodeName, slurmConfig=config)
        defer.returnValue(self)


    @defer.inlineCallbacks
    def release(self):
        remote = yield self.connectionProvider.getConnection()
        yield remote.callRemote(commands.DestroyDomain, nodeName=self.nodeName)
        defer.returnValue(self)


    def getConfigEntry(self):
        return 'NodeName={self.nodeName} NodeHostname={self.hostname} ' \
                'Port={self.port}'.format(self=self)



class Provisioner(object):

    implements(resources.IResourceProvisioner)


    def __init__(self, reactor, config):
        self.log = logging.Logger(__name__)

        self.nodes = spread.ReconnectingConnectionsPool(reactor, amp.AMP,
                config.get('libvirt', 'nodes').splitlines())
        self.nodes.start()

        self.reactor = reactor
        self.config = config


    def getNodes(self, count, names, **kwargs):
        nodes = []

        with open(self.config.get('libvirt', 'domainXML')) as fh:
            description = etree.parse(fh)

        # TODO: Transfer disk images to nodes

        # TODO: Refactor this to first choose all nodes and then requesting the
        #       VMs, this allows to select the best strategy to transfer the
        #       disk images.

        @defer.inlineCallbacks
        def gotPhysicalNode(node, nodeName, description):
            domainData = yield node.callRemote(commands.CreateDomain,
                    description=description)
            domain = VirtualNode(self, node.factory, nodeName, **domainData)
            defer.returnValue(domain)

        for _ in range(count):
            nodeName = next(names)
            description.find('name').text = nodeName

            d = self.nodes.getNextConnection()
            d.addCallback(gotPhysicalNode, nodeName, description)

            nodes.append(d)

        return nodes
