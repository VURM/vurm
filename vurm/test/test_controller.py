
import ConfigParser
import os

from vurm import controller, error, resources

from twisted.internet import defer
from twisted.trial import unittest
from twisted.python import filepath

from zope.interface import implements



class FakeNode(object):

    implements(resources.INode)

    def __init__(self):
        self.spawned = False
        self.released = False

    def getConfigEntry(self):
        return ''


    def spawn(self):
        self.spawned = True
        return defer.succeed(self)


    def release(self):
        self.released = True
        return defer.succeed(self)



class FakeProvisioner(object):

    implements(resources.IResourceProvisioner)

    def __init__(self, nodeCount=None):
        self.nodeCount = nodeCount
        self.nodes = []

    def getNodes(self, count):
        if self.nodeCount is not None:
            count = min(self.nodeCount, count)
            self.nodeCount -= count

        nodes = [FakeNode() for i in range(count)]
        self.nodes += nodes
        return [defer.succeed(n) for n in nodes]



class ControllerTestCaseBse(unittest.TestCase):

    def setUp(self):
        # Create configuration object
        self.config = ConfigParser.RawConfigParser()
        self.config.add_section('vurmctld')

        # Update configuration with temporary slurm config file
        self.tmpConfig = filepath.FilePath(self.mktemp())
        self.config.set('vurmctld', 'slurmconfig', self.tmpConfig.path)

        # Get the path of the reconfigure test helper
        self.reconfigureScript = filepath.FilePath(__file__).parent().child(
                'reconfigurator_exec.py').path

        cmd = 'python {0} succeed'.format(self.reconfigureScript)
        self.config.set('vurmctld', 'reconfigure', cmd)

        self.resetConfig()


    def controllerWithProvisioners(self, *counts):
        return controller.VurmController(self.config,
                [FakeProvisioner(count) for count in counts])


    def tearDown(self):
        if self.tmpConfig.exists():
            self.tmpConfig.remove()


    def resetConfig(self, content=''):
        with self.tmpConfig.open('w') as fh:
            fh.write(content)



class ControllerClusterDestroyTestCase(ControllerTestCaseBse):

    @defer.inlineCallbacks
    def test_nodesRelease(self):
        provisioner = FakeProvisioner(5)

        ctrl = controller.VurmController(self.config, [provisioner])
        name = yield ctrl.remote_createVirtualCluster(5)

        yield ctrl.remote_destroyVirtualCluster(name)

        for n in provisioner.nodes:
            self.assertTrue(n.spawned)
            self.assertTrue(n.released)


    def test_invalidName(self):
        ctrl = controller.VurmController(self.config, ())

        return self.failUnlessFailure(
            ctrl.remote_destroyVirtualCluster('somename'),
            error.InvalidClusterName
        )


    @defer.inlineCallbacks
    def test_reconfigurationError(self):
        provisioner = FakeProvisioner()

        ctrl = controller.VurmController(self.config, [provisioner])
        name = yield ctrl.remote_createVirtualCluster(5)

        cmd = 'python {0} fail'.format(self.reconfigureScript)
        self.config.set('vurmctld', 'reconfigure', cmd)

        try:
            yield ctrl.remote_destroyVirtualCluster(name)
        except error.ReconfigurationError:
            for n in provisioner.nodes:
                self.assertTrue(n.spawned)
                self.assertTrue(n.released)

            # Cluster shall not exist anymore
            yield self.failUnlessFailure(
                ctrl.remote_destroyVirtualCluster(name),
                error.InvalidClusterName
            )

            defer.returnValue(None)

        raise unittest.FailTest()



class ControllerClusterCreationTestCase(ControllerTestCaseBse):


    def assertCreationSucceeds(self, ctrl, size, minSize=None):
        return ctrl.remote_createVirtualCluster(size, minSize)


    def assertCreationFails(self, ctrl, size, minSize=None):
        return self.failUnlessFailure(
            ctrl.remote_createVirtualCluster(size, minSize),
            error.InsufficientResourcesException
        )


    def test_fixedCreation(self):
        ctrl = self.controllerWithProvisioners(None)
        return self.assertCreationSucceeds(ctrl, 5)


    def test_minCreation(self):
        ctrl = self.controllerWithProvisioners(7)
        return self.assertCreationSucceeds(ctrl, 10, 5)


    def test_minCreationFail(self):
        ctrl = self.controllerWithProvisioners(4)
        return self.assertCreationFails(ctrl, 10, 5)


    def test_failCreation(self):
        ctrl = self.controllerWithProvisioners(5)
        return self.assertCreationFails(ctrl, 10)


    def test_multipleProvisioner(self):
        ctrl = self.controllerWithProvisioners(5, 5, 5, 5)
        return self.assertCreationSucceeds(ctrl, 13)


    def test_multipleProvisionersFail(self):
        ctrl = self.controllerWithProvisioners(5, 5, 5, 5)
        return self.assertCreationFails(ctrl, 23)


    def test_noProvisionersFail(self):
        ctrl = self.controllerWithProvisioners()
        return self.assertCreationFails(ctrl, 1)


    @defer.inlineCallbacks
    def test_multipleClusters(self):
        ctrl = self.controllerWithProvisioners(5, 5, 5, 5)
        yield self.assertCreationSucceeds(ctrl, 7)
        yield self.assertCreationSucceeds(ctrl, 7)
        yield self.assertCreationFails(ctrl, 7)


    @defer.inlineCallbacks
    def test_nodesCreated(self):
        provisioner = FakeProvisioner()

        ctrl = controller.VurmController(self.config, [provisioner])
        yield ctrl.remote_createVirtualCluster(5)

        self.assertEquals(5, len(provisioner.nodes))


    @defer.inlineCallbacks
    def test_nodesSpawned(self):
        provisioner = FakeProvisioner()

        ctrl = controller.VurmController(self.config, [provisioner])
        yield ctrl.remote_createVirtualCluster(5)

        for n in provisioner.nodes:
            self.assertTrue(n.spawned)
            self.assertFalse(n.released)


    @defer.inlineCallbacks
    def test_nodesReleasedInsufficientResources(self):
        provisioner = FakeProvisioner(5)

        ctrl = controller.VurmController(self.config, [provisioner])

        try:
            yield ctrl.remote_createVirtualCluster(10)
        except error.InsufficientResourcesException:
            for n in provisioner.nodes:
                self.assertFalse(n.spawned)
                self.assertTrue(n.released)
            defer.returnValue(None)

        raise unittest.FailTest()


    @defer.inlineCallbacks
    def test_nodesReleasedReconfigurationError(self):
        provisioner = FakeProvisioner(5)

        cmd = 'python {0} fail'.format(self.reconfigureScript)
        self.config.set('vurmctld', 'reconfigure', cmd)

        ctrl = controller.VurmController(self.config, [provisioner])

        try:
            yield ctrl.remote_createVirtualCluster(5)
        except error.ReconfigurationError:
            for n in provisioner.nodes:
                self.assertFalse(n.spawned)
                self.assertTrue(n.released)
            defer.returnValue(None)

        raise unittest.FailTest()



class ControllerReconfigureTestCase(ControllerTestCaseBse):

    def setUp(self):
        super(ControllerReconfigureTestCase, self).setUp()

        # Create new controller instance
        self.controller = controller.VurmController(self.config, ())


    def test_scontrolFail(self):
        """
        Tests that the correct error is throw if the scontrol command fails
        """

        cmd = 'python {0} fail'.format(self.reconfigureScript)
        self.config.set('vurmctld', 'reconfigure', cmd)

        return self.failUnlessFailure(
            self.controller.updateSlurmConfig(add='add', notify=True),
            error.ReconfigurationError
        )


    @defer.inlineCallbacks
    def test_scontrolCalled(self):
        """
        Tests that the scontrol command is called with the correct arguments.
        """

        self.resetConfig('remove')

        temp = self.mktemp()

        cmd = 'python {0} callback {1}'.format(self.reconfigureScript, temp)
        self.config.set('vurmctld', 'reconfigure', cmd)

        yield self.controller.updateSlurmConfig(remove='remove', notify=True)

        with open(temp) as fh:
            self.assertEquals(fh.read(), 'called')

        os.remove(temp)


    def test_invalidArgs(self):
        return self.failUnlessFailure(
            self.controller.updateSlurmConfig(notify=False),
            TypeError
        )


    @defer.inlineCallbacks
    def test_add(self):
        """
        Test that adding some values to the configuration file works as
        expected.
        """

        yield self.controller.updateSlurmConfig(add='add', notify=False)

        with self.tmpConfig.open() as fh:
            self.assertEquals(fh.read(), 'add')


    @defer.inlineCallbacks
    def test_remove(self):
        """
        Test that removing values from the configuration file works as
        expected.
        """

        self.resetConfig('remove')

        yield self.controller.updateSlurmConfig(remove='remove', notify=False)

        with self.tmpConfig.open() as fh:
            self.assertEquals(fh.read(), '')
