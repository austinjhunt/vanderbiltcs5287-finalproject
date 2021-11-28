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

class DataManager:
    def __init__(self, username="", password="", verbose=False, leader_address=""):
        self.username = username
        self.password = password
        self.verbose = verbose
        self.setup_logging(verbose=verbose)
        self.leader_address = leader_address
        self.random_data_generator = RandomDocumentGenerator()
        self.database_operation_commander = OperationCommander()
        self.couchbase_endpoint = f'couchbase://{self.leader_address}'
        self.cluster = Cluster(
            self.couchbase_endpoint,
            authenticator=PasswordAuthenticator(
                self.username,
                self.password
            )
        )
        self.bucket_ram_quota_mb = 1024
        self.bucket_replica_number = 2

    def set_bucket_replica_number(self, new_replica_number):
        self.info(f'Updating bucket replica number from {self.bucket_replica_number} to {new_replica_number}')
        self.bucket_replica_number = new_replica_number

    def setup_logging(self, verbose=False):
        """ set up self.logger for Driver logging """
        self.logger = logging.getLogger('DataManager')
        formatter = logging.Formatter('%(prefix)s - %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.prefix = {'prefix': 'Data Manager'}
        self.logger.addHandler(handler)
        self.logger = logging.LoggerAdapter(self.logger, self.prefix )
        if verbose:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug('Debug mode enabled', extra=self.prefix )
        else:
            self.logger.setLevel(logging.INFO)

    def debug(self, msg):
        self.logger.debug(msg, extra=self.prefix)

    def info(self, msg):
        self.logger.info(msg, extra=self.prefix)

    def error(self, msg):
        self.logger.error(msg, extra=self.prefix)

    def install_sample_bucket(self):
        """ Install sample bucket on cluster using couchbase url provided on init
        using the REST API for couchbase. NOT USED in favor of local RandomDocumentGenerator """
        self.info(f"Installing the travel-sample bucket at {self.leader_address} REST API endpoint")
        install_sample_bucket_url = f'http://{self.leader_address}:8091/sampleBuckets/install'
        data = ["travel-sample"]
        response = requests.post(install_sample_bucket_url, data=json.dumps(data), auth=(self.username,self.password))
        self.info(response.json())

    def create_primary_index(self, bucket_name=""):
        # index_name = f'default_primary_index_{bucket_name.replace("-","_")}'
        index_name = ''
        self.info(f'Creating primary index {index_name} on `{bucket_name}`;')
        # response = self.cluster.query(f'CREATE PRIMARY INDEX {index_name} ON `{bucket_name}`')
        #
        # Fix error: Caused by: com.couchbase.client.core.CouchbaseException: N1qlQuery Error - {"msg":"No
        # index available on keyspace `default`:`ycsb_test_bucket` that matches your query.
        #  Use CREATE PRIMARY INDEX ON `default`:`ycsb_test_bucket` to create a primary index,
        # or check that your expected index is online.","code":4000}
        response = self.cluster.query(f'CREATE PRIMARY INDEX ON `default`:`{bucket_name}`')
        for r in response.rows():
            self.info(r)
        return response

    def create_bucket(self, bucket_name="", bucket_ram_quota_mb=1024, bucket_replicas=0):
        """ Create and return a bucket """
        self.info(
            f"Creating bucket {bucket_name} with RAM quota {bucket_ram_quota_mb}MB "
            f"and {bucket_replicas} replicas"
            )
        create_bucket_cmd = (
            f'couchbase-cli bucket-create '
            f'-c {self.couchbase_endpoint} '
            f'--username {self.username} '
            f'--password {self.password} '
            f'--bucket {bucket_name} '
            f'--bucket-type couchbase '
            f'--durability-min-level none '
            f'--bucket-ramsize {bucket_ram_quota_mb} '
            f'--bucket-replica {bucket_replicas} '
            f'--enable-flush 1 '
            f'--conflict-resolution sequence '
            f'--wait '
        )
        process = subprocess.Popen(create_bucket_cmd.split())
        output, error = process.communicate()
        if output and output != "None":
            self.info(output)
        if error and error != "None":
            if "Bucket with given name already exists" in error:
                # Simply update the replica number
                self.info(f'Bucket {bucket_name} already exists, just applying updates (updated_replica_num={self.bucket_replica_number})')
                create_bucket_cmd = (
                    f'couchbase-cli bucket-edit '
                    f'-c {self.couchbase_endpoint} '
                    f'--username {self.username} '
                    f'--password {self.password} '
                    f'--bucket {bucket_name} '
                    f'--bucket-type couchbase '
                    f'--durability-min-level none '
                    f'--bucket-ramsize {self.bucket_ram_quota_mb} '
                    f'--bucket-replica {self.bucket_replica_number} '
                    f'--enable-flush 1 '
                    f'--conflict-resolution sequence '
                    f'--wait '
                )
                process = subprocess.Popen(create_bucket_cmd.split())
                output, error = process.communicate()
                if output and output != "None":
                    self.info(output)
                if error and error != "None":
                    self.error(error)
        return output

    def create_scope(self, scope_name="", bucket_name=""):
        """ Create a collection """
        self.info(f'Creating scope {scope_name} on bucket {bucket_name}')
        cmd = (
            f'couchbase-cli collection-manage '
            f'--cluster {self.couchbase_endpoint} '
            f'--username {self.username} '
            f'--password {self.password} '
            f'--create-scope {scope_name} '
            f'--bucket {bucket_name}'
        )
        process = subprocess.Popen(cmd.split())
        output, error = process.communicate()
        if error and error != "None":
            self.error(error)
        self.debug(output)
        return output

    def create_collection(self, bucket_name="", scope_name="", collection_name=""):
        """ Create a collection """
        self.info(f'Creating collection {collection_name} on bucket {bucket_name}')
        cmd = (
            f'couchbase-cli collection-manage --cluster {self.couchbase_endpoint} '
            f'--username {self.username} --password {self.password} '
            f'--create-collection {scope_name}.{collection_name} '
            f'--bucket {bucket_name}'
        )
        process = subprocess.Popen(cmd.split())
        output, error = process.communicate()
        if error and error != "None":
            self.error(error)
        self.debug(output)
        return output

    def drop_bucket(self, bucket_name=""):
        """ Drop a bucket from the database """
        cmd = (
            f'couchbase-cli bucket-delete '
            f'--cluster {self.couchbase_endpoint} '
            f'--username {self.username} '
            f'--password {self.password} '
            f'--bucket {bucket_name}'
        )
        process = subprocess.Popen(cmd, shell=True)
        output, error = process.communicate()
        if error and error != "None":
            self.error(error)
        if output and output != "None":
            self.info(output)
        return output

    def flush_bucket(self, bucket_name=""):
        self.info(f"Flushing bucket {bucket_name}")
        cmd = (
            f'echo "Yes" | couchbase-cli bucket-flush --cluster {self.couchbase_endpoint} --username {self.username} '
            f'--password {self.password} --bucket {bucket_name}'
        )
        process = subprocess.Popen(cmd, shell=True)
        output, error = process.communicate()
        if error and error != "None":
            self.error(error)
        if output and output != "None":
            self.info(output)
        return output

    def init_data_file(self, cluster_size=1, bucket_name="small-bucket", operation="insert",  durability_level=""):
        """ Initialize an empty file to which operation latency data can be written during execution;
        Use cluster_size + 1 for folder name because cluster_size excludes leader. (cluster_size = 0 is just leader) """
        folder = f'data/durability-{durability_level}/cluster-size-{cluster_size + 1}/{bucket_name}/{operation}'
        full_folder = os.path.join(
            os.path.dirname(__file__), folder
        )
        # Make sure folder exists
        Path(full_folder).mkdir(parents=True, exist_ok=True)
        data_file = f'{full_folder}/latencies.txt'
        return data_file


    def run_inserts(self, cluster_size=1, bucket_name="", num_docs=1000, operations_to_record=100,durability_level="low"):
        """ Insert num_docs random JSON documents into the specified bucket """
        # Write all the insert latency data to this file
        data_file_name = self.init_data_file(
            cluster_size=cluster_size,
            bucket_name=bucket_name,
            operation='insert',
            durability_level=durability_level
        )
        self.info(f'Running {num_docs} Insert operations (only RECORDING {operations_to_record})...')
        operations_recorded = 0
        with yaspin().white.bold.shark.on_blue as sp:
            for i in range(num_docs):
                # Create an Insert operation object and execute it with commander.
                # Insert one of the pre-generated random JSON documents.
                self.database_operation_commander.execute_operation(
                    operation=InsertOperation(
                        verbose=self.verbose,
                        data_file_name=data_file_name,
                        cluster=self.cluster,
                        bucket_name=bucket_name,
                        insert_doc=self.random_data_generator.get_random_json_doc(),
                        doc_key=i,
                        durability_level=durability_level),
                    record_operation_latency=(operations_recorded < operations_to_record)
                    )
                operations_recorded += 1

    def run_n1ql_selects(self,  cluster_size=1, bucket_name="", operations_to_record=100,durability_level="low"):
        """ Run operations_to_record N1QLQueryOperations on provide bucket """
        data_file_name = self.init_data_file(
            cluster_size=cluster_size,
            bucket_name=bucket_name,
            operation="n1qlselect",
            durability_level=durability_level)
        self.info(f'Running {operations_to_record} N1QL SELECT [...] operations...')
        with yaspin().white.bold.shark.on_blue as sp:
            for i in range(operations_to_record):
                # Create an Insert operation object and execute it with commander.
                # Insert one of the pre-generated random JSON documents.
                self.database_operation_commander.execute_operation(
                    operation=N1QLQueryOperation(
                        verbose=self.verbose,
                        data_file_name=data_file_name,
                        cluster=self.cluster,
                        bucket_name=bucket_name,
                        vandy_phrase=self.random_data_generator.random_vandy_phrase()
                    ),
                    record_operation_latency=True
                    )

    def run_full_text_searches(self,  cluster_size=1, bucket_name="", operations_to_record=100,durability_level="low"):
        """ Run operations_to_record N1QLQueryOperations on provide bucket """
        # Write all the insert latency data to this file
        self.info(f'Running {operations_to_record} Full Text Search operations...')
        data_file_name = self.init_data_file(
            cluster_size=cluster_size,
            bucket_name=bucket_name,
            operation="fts",
            durability_level=durability_level
        )
        with yaspin().white.bold.shark.on_blue as sp:
            for i in range(operations_to_record):
                # Create an Insert operation object and execute it with commander.
                # Insert one of the pre-generated random JSON documents.
                self.database_operation_commander.execute_operation(
                    operation=FullTextSearchOperation(
                        verbose=self.verbose,
                        data_file_name=data_file_name,
                        cluster=self.cluster,
                        bucket_name=bucket_name,
                        vandy_phrase=self.random_data_generator.random_vandy_phrase()
                    ),
                    record_operation_latency=True
                )

    def run_updates(self, cluster_size=1, bucket_name="", operations_to_record=100,durability_level="low"):
        self.info(f'Running {operations_to_record} Update operations...')
        data_file_name = self.init_data_file(
            cluster_size=cluster_size,
            bucket_name=bucket_name,
            operation='update',
            durability_level=durability_level)
        with yaspin().white.bold.shark.on_blue as sp:
            for i in range(operations_to_record):
                self.database_operation_commander.execute_operation(
                    UpdateOperation(
                        verbose=self.verbose,
                        data_file_name=data_file_name,
                        cluster=self.cluster,
                        bucket_name=bucket_name,
                        doc_replace_value=self.random_data_generator.get_random_json_doc(),
                        doc_key=i,
                        durability_level=durability_level),
                        record_operation_latency=True
                    )

    def delete_docs_in_bucket(self, cluster_size=1, bucket_name="", operations_to_record=100,durability_level="low"):
        self.info(f'Running {operations_to_record} Delete operations...')
        data_file_name = self.init_data_file(
            cluster_size=cluster_size,
            bucket_name=bucket_name,
            operation='delete',
            durability_level=durability_level)
        with yaspin().white.bold.shark.on_blue as sp:
            for i in range(operations_to_record):
                self.database_operation_commander.execute_operation(
                    DeleteOperation(
                        verbose=self.verbose,
                        data_file_name=data_file_name,
                        cluster=self.cluster,
                        bucket_name=bucket_name,
                        doc_key=i,
                        durability_level=durability_level),
                        record_operation_latency=True
                    )


