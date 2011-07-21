

import ConfigParser
import random

from twisted.trial import unittest
from twisted.python import filepath
from twisted.internet import reactor, defer
from twisted.internet.error import ProcessDone

from vurm.provisioners import multilocal
from vurm import resources



class ProvisionerTestCase(unittest.TestCase):

    def setUp(self):
        # Create configuration object
        self.config = ConfigParser.RawConfigParser()
        self.config.add_section('multilocal')

        self.config.set('multilocal', 'baseport', 0)
        self.config.set('multilocal', 'slurmd', '')

    def test_portNumbers(self):
        multilocal.Provisioner._Provisioner__currentPort = None

        def provisioner():
            return multilocal.Provisioner(reactor, self.config)
        provisioners = [provisioner() for i in range(10)]

        for i in range(100):
            p = random.choice(provisioners)
            self.assertEquals(p.getNextPort(), i)


    @defer.inlineCallbacks
    def test_getNodes(self):
        """
        Test that getNodes returns a list of deferreds and that each of the
        results can be adapted to the INode interface.
        """

        provisioner = multilocal.Provisioner(reactor, self.config)

        def adapt(node):
            return resources.INode(node)

        nodeNames = (str(i) for i in range(20))
        nodeCallbacks = provisioner.getNodes(20, nodeNames)

        self.assertEquals(len(nodeCallbacks), 20)

        nodes = [nCb.addCallback(adapt) for nCb in nodeCallbacks]

        yield defer.gatherResults(nodes)


class LocalNodeTestCase(unittest.TestCase):

    def setUp(self):
        # Create configuration object
        self.config = ConfigParser.RawConfigParser()
        self.config.add_section('multilocal')

        self.tmpConfig = filepath.FilePath(self.mktemp())

        # Get the path of the reconfigure test helper
        self.reconfigureScript = filepath.FilePath(__file__).parent().child(
                'node_exec.py').path


    def getNode(self, command, nodeName='nodename'):
        cmd = 'python {0} {1} {2} {{nodeName}} {{hostname}} {{port}}'.format(
            self.reconfigureScript, command, self.tmpConfig.path)
        self.config.set('multilocal', 'slurmd', cmd)

        node = multilocal.LocalNode(nodeName, cmd, 1, reactor)

        return node


    def tearDown(self):
        if self.tmpConfig.exists():
            self.tmpConfig.remove()


    def test_attributes(self):
        # Set a nodename
        node = self.getNode('succeed')

        # Check INode interface attributes
        self.assertEquals(node.port, 1)
        self.assertEquals(node.nodeName, 'nodename')
        self.assertEquals(node.hostname, 'localhost')


    def test_config(self):
        # Set a nodename
        node = self.getNode('succeed')

        # Check INode interface attributes
        self.assertEquals(node.getConfigEntry(),
                'NodeName=nodename NodeHostname=localhost Port=1')


    @defer.inlineCallbacks
    def test_nodeOutput(self):
        """
        Tests that node output on both stdout or stderr does not throw any
        errors.
        """

        node = self.getNode('print')

        node.spawn()

        yield self.failUnlessFailure(node.stopped, ProcessDone)


    @defer.inlineCallbacks
    def test_spawn(self):
        node = self.getNode('callback')

        node.spawn()

        yield self.failUnlessFailure(node.stopped, ProcessDone)

        # Check file for correct values
        with self.tmpConfig.open() as fh:
            nodename, hostname, port = fh.read().split('|')

        self.assertEquals(int(port), 1)
        self.assertEquals(nodename, 'nodename')
        self.assertEquals(hostname, 'localhost')


    @defer.inlineCallbacks
    def test_spawnTerminate(self):
        node = self.getNode('sleep')

        yield node.spawn()

        d = defer.Deferred()

        def terminate(node, d):
            node.terminate().addCallback(d.callback)
        reactor.callLater(1, terminate, node, d)

        yield d


    @defer.inlineCallbacks
    def test_spawnRelease(self):
        node = self.getNode('sleep')

        yield node.spawn()

        d = defer.Deferred()

        def release(node, d):
            node.release().addCallback(d.callback)
        reactor.callLater(1, release, node, d)

        yield d


    @defer.inlineCallbacks
    def test_spawnSpawned(self):
        node = self.getNode('sleep')

        # This should not raise
        yield node.spawn()

        # This should
        self.failUnlessRaises(RuntimeError, node.spawn)

        yield node.release()


    @defer.inlineCallbacks
    def test_stopNotRunning(self):
        node = self.getNode('succeed')

        # This should raise
        self.failUnlessRaises(RuntimeError, node.terminate)

        # This should not
        yield node.release()
