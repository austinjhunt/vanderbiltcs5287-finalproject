from lib.ClusterManager import ClusterManager
from lib.DataManager import DataManager
import subprocess
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from lib.Operations import (
    FullTextSearchOperation, InsertOperation, N1QLQueryOperation,
    OperationCommander,UpdateOperation,DeleteOperation
)
from lib.RandomDocumentGenerator import RandomDocumentGenerator
import requests
import json
import logging
import os
import random
import string
from pathlib import Path
from yaspin import yaspin

DEFAULT_SCOPE = "default_scope"
DEFAULT_COLLECTION = "default_collection"

class TestDataManager:
    def setUp(self):
        self.clusterman = ClusterManager(username='admin',password='123456',verbose=False)
        self.dataman = DataManager(username='admin', password='123456', verbose=False,
            leader_address=self.clusterman.get_public_address(self.clusterman.get_leader()) )

    def test_set_bucket_replica_number(self, new_replica_number):
        self.info(f'Updating bucket replica number from {self.bucket_replica_number} to {new_replica_number}')
        self.bucket_replica_number = new_replica_number

