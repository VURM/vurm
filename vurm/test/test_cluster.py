
import itertools

from vurm import cluster

from twisted.trial import unittest



class SettingsTestCase(unittest.TestCase):

    def setUp(self):
        pass


    def tearDown(self):
        pass


    def test_nameIsUnique(self):
        c = cluster.CLUSTER_NAME_CHARS
        l = cluster.CLUSTER_NAME_LENGTH
        p = cluster.CLUSTER_NAME_PREFIX

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

        cluster.CLUSTER_NAME_CHARS = c
        cluster.CLUSTER_NAME_LENGTH = l
        cluster.CLUSTER_NAME_PREFIX = p
