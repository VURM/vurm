
import itertools

from vurm import cluster

from twisted.trial import unittest



class SettingsTestCase(unittest.TestCase):

    def setUp(self):
        self.old_cluster_name_chars = cluster.CLUSTER_NAME_CHARS
        self.old_cluster_name_length = cluster.CLUSTER_NAME_LENGTH
        self.old_cluster_name_prefix = cluster.CLUSTER_NAME_PREFIX
        self.old_node_name_prefix = cluster.NODE_NAME_PREFIX


    def tearDown(self):
        cluster.CLUSTER_NAME_CHARS = self.old_cluster_name_chars
        cluster.CLUSTER_NAME_LENGTH = self.old_cluster_name_length
        cluster.CLUSTER_NAME_PREFIX = self.old_cluster_name_prefix
        cluster.NODE_NAME_PREFIX = self.old_node_name_prefix


    def test_nodeNamesGenerator(self):
        cluster.CLUSTER_NAME_PREFIX = ''
        cluster.NODE_NAME_PREFIX = ''
        names = cluster.VirtualCluster.nodeNamesGenerator('')

        for i in range(10):
            self.assertEquals(i, int(next(names)[1:]))


    def test_nameIsUnique(self):
        cluster.CLUSTER_NAME_CHARS = 'ABC'
        cluster.CLUSTER_NAME_LENGTH = 2
        cluster.CLUSTER_NAME_PREFIX = ''

        names = set(map(''.join, itertools.product(cluster.CLUSTER_NAME_CHARS,
                repeat=cluster.CLUSTER_NAME_LENGTH)))
        cluster.VirtualCluster._VirtualCluster__clusterNames = names

        name = names.pop()
        self.assertEquals(name, cluster.VirtualCluster.generateClusterName())

        name = names.pop()
        self.assertEquals(name, cluster.VirtualCluster.generateClusterName())

        name = names.pop()
        self.assertEquals(name, cluster.VirtualCluster([]).name)
