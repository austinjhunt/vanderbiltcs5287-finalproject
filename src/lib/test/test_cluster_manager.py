
from lib.ClusterManager import ClusterManager
import subprocess
import json
import os
import random
import unittest
class TestClusterManager(unittest.TestCase):
    def setUp(self):
        self.cluster_manager = ClusterManager('admin','123456', False)

    def test_get_max_cluster_size(self):
        _max = self.cluster_manager.get_max_cluster_size()
        self.assertEqual(_max, len(self.cluster_manager.hosts))

    def test_get_hosts_from_json(self):
        hosts_file = f'{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}/hosts.json'
        hosts = []
        try:
            with open(hosts_file) as f:
                hosts = json.load(f)['hosts']
                self.assertTrue(isinstance(hosts, list))
                self.assertEqual(len(self.cluster_manager.hosts), len(hosts))
        except Exception as e:
            print(e)
            self.assertTrue(False)


    def test_randomly_assign_host_roles(self):
        """ Randomly select one of self.hosts as leader, rest as followers """
        self.cluster_manager.randomly_assign_host_roles()
        self.assertTrue(self.cluster_manager.get_leader() != None)
        self.assertTrue(self.cluster_manager.get_followers() != None)
        self.assertEqual(len(self.cluster_manager.hosts) - 1, len(self.cluster_manager.get_followers()))

    def test_get_leader(self):
        self.assertTrue(self.cluster_manager.get_leader() != None)
        self.assertTrue(isinstance(self.cluster_manager.get_leader(), dict))
        self.assertTrue("public" in self.cluster_manager.get_leader())
        self.assertTrue("private" in self.cluster_manager.get_leader())

    def test_get_followers(self):
        self.assertTrue(self.cluster_manager.get_followers() != None)
        self.assertTrue(isinstance(self.cluster_manager.get_followers(), list))
        self.assertTrue(all(isinstance(x, dict) for x in self.cluster_manager.get_followers()))
        self.assertTrue(all("public" in x for x in self.cluster_manager.get_followers()))
        self.assertTrue(all("private" in x for x in self.cluster_manager.get_followers()))

    def test_get_public_address(self):
        self.assertTrue(isinstance(self.cluster_manager.get_public_address(self.cluster_manager.get_leader()),str))

    def test_get_private_address(self):
        self.assertTrue(isinstance(self.cluster_manager.get_private_address(self.cluster_manager.get_leader()),str))

