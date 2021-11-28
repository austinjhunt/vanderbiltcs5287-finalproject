""" Driver module that drives the testing framework for Couchbase. You first need to create some pool of servers (with Couchbase installed on each of them)
(e.g. with AWS EC2) and simply provide their addresses to the driver as --host <IP1> --host <IP2> ... --host <IPN>"""

import argparse
import logging
import subprocess
from lib.Analyzer import Analyzer
from lib.ClusterManager import ClusterManager
from lib.DataManager import DataManager
from pathlib import Path

class Driver:
    def __init__(self, username="", password="", verbose=False,
                 data_sample_size=1000,
                 small_data_sample_size=1000,
                 medium_data_sample_size=3000,
                 large_data_sample_size=5000,
                 operation_sample_size=100,
                 default_scope="default_scope",
                 default_collection="default_collection"):
        self.cluster_manager = ClusterManager(username, password, verbose)
        # Tell the data manager what the public address of the cluster leader is
        self.data_manager = DataManager(username=username, password=password, verbose=verbose,
            leader_address=self.cluster_manager.get_public_address(self.cluster_manager.get_leader()))
        self.admin_username = username
        self.admin_password = password
        self.data_sample_size = data_sample_size
        self.operation_sample_size = operation_sample_size
        self.small_data_sample_size = small_data_sample_size
        self.medium_data_sample_size = medium_data_sample_size
        self.large_data_sample_size = large_data_sample_size
        self.default_scope = default_scope
        self.default_collection = default_collection
        self.setup_logging(verbose)

    def get_cluster_manager(self):
        return self.cluster_manager

    def get_data_manager(self):
        return self.data_manager

    def setup_logging(self, verbose):
        """ set up self.logger for Driver logging """
        self.logger = logging.getLogger('driver')
        formatter = logging.Formatter('%(prefix)s - %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.prefix = {'prefix': 'DRIVER'}
        self.logger.addHandler(handler)
        self.logger = logging.LoggerAdapter(self.logger, self.prefix)
        if verbose:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug('Debug mode enabled', extra=self.prefix)
        else:
            self.logger.setLevel(logging.INFO)

    def _ycsb(self,
        use_workload_template=False,
        workload='a',
        url='',
        host='',
        bucket='',
        password='',
        persistTo=0,
        replicateTo=0,
        fieldcount=10,
        fieldlength=100,
        recordcount=1000000,
        operationcount=3000000,
        readproportion=0.5,
        updateproportion=0.5,
        scanproportion=0,
        insertproportion=0,
        requestdistribution='zipfian',
        measurementtype='raw'
        ):

        if use_workload_template:
            # YCSB driven by config file
            properties = (
                f' -p couchbase.host={host} '
                f' -p couchbase.bucket={bucket} '
                f' -p couchbase.password={password} '
                f' -p couchbase.persistTo={persistTo} '
                f' -p couchbase.replicateTo={replicateTo} '
                f' -p measurementtype={measurementtype} '
            )
            # Before you can actually run the workload, you need to "load" the data first.
            load_data_cmd = (
                f'ycsb/bin/ycsb load couchbase2 -s -P ycsb/workloads/workload{workload} '
                f'{properties}'
            )
            self.info(f"RUNNING YSCB LOAD DATA COMMAND: \n{load_data_cmd}")
            process = subprocess.Popen(load_data_cmd.split())
            output, error = process.communicate()
            if error:
                self.error(f'Error: {error}')
            run_workload_cmd = (
                f'ycsb/bin/ycsb run couchbase2 -s -P ycsb/workloads/workload{workload} '
                f'{properties}'
            )
        else:
            # YCSB fully driven by runtime args, not config file
            properties = (
                f' -p couchbase.host={host} '
                f' -p couchbase.bucket={bucket} '
                f' -p couchbase.password={password} '
                f' -p couchbase.persistTo={persistTo} '
                f' -p couchbase.replicateTo={replicateTo} '
                f' -p fieldcount={fieldcount} '
                f' -p fieldlength={fieldlength} '
                f' -p recordcount={recordcount} '
                f' -p operationcount={operationcount} '
                f' -p workload=site.ycsb.workloads.CoreWorkload '
                f' -p readallfields=true '
                f' -p readproportion={readproportion} '
                f' -p updateproportion={updateproportion} '
                f' -p scanproportion={scanproportion} '
                f' -p insertproportion={insertproportion} '
                f' -p requestdistribution={requestdistribution} '
                f' -p measurementtype={measurementtype} '
            )
            load_data_cmd =  f'ycsb/bin/ycsb load couchbase2 -s {properties}'
            self.info(f"RUNNING YSCB LOAD DATA COMMAND: \n{load_data_cmd}")
            process = subprocess.Popen(load_data_cmd.split())
            output, error = process.communicate()
            if error:
                self.error(f'Error: {error}')
            run_workload_cmd = f'ycsb/bin/ycsb run couchbase2 -s {properties}'

            self.info(f"RUNNING YSCB RUN COMMAND: \n{run_workload_cmd}")
        process = subprocess.Popen(run_workload_cmd.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        if error:
            self.error(f'Error: {error}')
        return output.decode()

    def run_ycsb(self):
        """ Use YCSB to analyze performance of various cluster configurations """
        CLUSTER_SIZE = 4 # leader + 4 nodes
        BUCKET_NAME = 'ycsb_test_bucket'
        self.cluster_manager.setup_cluster_colocated_services( cluster_size=CLUSTER_SIZE )
        self.data_manager.create_bucket(bucket_name=BUCKET_NAME, bucket_ram_quota_mb=1024, bucket_replicas=0)
        self.cluster_manager.create_user_for_bucket(username=BUCKET_NAME,password=BUCKET_NAME,bucket_name=BUCKET_NAME)
        self.data_manager.flush_bucket(bucket_name=BUCKET_NAME)
        # create a scope, then a collection
        self.data_manager.create_scope(scope_name=self.default_scope, bucket_name=BUCKET_NAME)
        # CREATE PRIMARY INDEX ON bucket
        self.data_manager.create_primary_index(bucket_name=BUCKET_NAME)
        self.data_manager.create_collection(bucket_name=BUCKET_NAME, scope_name=self.default_scope, collection_name=self.default_collection)

        operation_proportions = [
            {
                'read': 0.75,
                'insert': 0.25
            },
            {
                'read': 1
            },
            {
                'read': 0.75,
                'update': 0.25,
            },

            {
                'read': .5,
                'update': .5,
            },
            {
                'read': 0.5,
                'insert': 0.5
            },
            {
                'scan': 0.95,
                'insert': 0.05
            }
        ]

        for recordcount in [1000, 10000, 100000]:
            for fieldcount in [10, 100, 500]:
                for fieldlength_bytes in [10, 50, 100]: # num bytes for each field
                    for requestdistribution in ['zipfian', 'uniform', 'latest']:
                        for op_pro in operation_proportions:
                            output = self._ycsb(
                                use_workload_template=False,
                                host=self.cluster_manager.get_leader_address(),
                                bucket=BUCKET_NAME,
                                password=BUCKET_NAME,
                                persistTo=0,
                                replicateTo=0,
                                fieldcount=fieldcount,
                                fieldlength=fieldlength_bytes,
                                recordcount=recordcount,
                                operationcount=recordcount,
                                readproportion=op_pro.get('read',0),
                                updateproportion=op_pro.get('update',0),
                                scanproportion=op_pro.get('scan',0),
                                insertproportion=op_pro.get('insert',0),
                                requestdistribution=requestdistribution,
                                measurementtype="raw"
                            )

                            ycsb_output_filename = (
                                f'csz{CLUSTER_SIZE + 1}'
                                f'-rc{recordcount}'
                                f'-fc{fieldcount}'
                                f'-fl{fieldlength_bytes}'
                                f'-rd{requestdistribution}'
                                f'-r{op_pro.get("read",0)}'
                                f'-u{op_pro.get("update",0)}'
                                f'-s{op_pro.get("scan",0)}'
                                f'-i{op_pro.get("insert",0)}.data'
                            )

                            ycsb_log_folder = 'lib/data/ycsb-results'
                            Path(ycsb_log_folder).mkdir(parents=True, exist_ok=True)
                            with open(f'{ycsb_log_folder}/{ycsb_output_filename}', 'w') as f:
                                f.write(output)
                            self.info(output)

        # Flush bucket at the end
        self.data_manager.flush_bucket(
            bucket_name=BUCKET_NAME)

    def run_test_framework(self):
        """ Analyze the impact of increasingly tuning durability within Couchbase cluster on operation latency;
        Higher durability should cause longer latencies. """
        # https://docs.couchbase.com/python-sdk/current/howtos/kv-operations.html#durability
        # (majority, majorityAndPersistToActive, persistToMajority)
        for durability_level in ['low', 'medium', 'high']:
            self.info(
                f'\n'
                f'#####################################################################\n'
                f'################     DURABILITY={durability_level}      #######################\n'
                f'#####################################################################\n'
                f'\n'
            )
            for cluster_size in range(self.cluster_manager.get_max_cluster_size()):
                # cluster size = 0 means just leader; 1 means leader + 1 node, 2=> leader + 2 nodes, 3 => leader + 3 nodes, etc.
                self.info(
                    f'\n'
                    f'#####################################################################\n'
                    f'################# DURABILITY={durability_level},CLUSTER_SIZE={cluster_size+1} ############\n'
                    f'#####################################################################\n'
                    f'\n'
                )
                self.cluster_manager.setup_cluster_colocated_services(
                    cluster_size=cluster_size)
                for bucket_size_label, bucket_size_value in {
                    'small-bucket': self.small_data_sample_size,
                    'medium-bucket': self.medium_data_sample_size,
                    'large-bucket': self.large_data_sample_size
                }.items():
                    self.info(
                        f'\n'
                        f'#####################################################################\n'
                        f'############### DURABILITY={durability_level},CLUSTER_SIZE={cluster_size+1} ###############\n'
                        f'############### BUCKET_SIZE={bucket_size_label} (docs={bucket_size_value}) ###############\n'
                        f'#####################################################################\n'
                        f'\n'
                    )
                    # if there's more than just the leader in the cluster, use data replication
                    num_replicas = 0
                    if cluster_size >= 1:
                        num_replicas = 1
                    self.data_manager.set_bucket_replica_number(
                        new_replica_number=num_replicas)
                    bucket = self.data_manager.create_bucket(
                        bucket_name=bucket_size_label)
                    self.data_manager.flush_bucket(
                        bucket_name=bucket_size_label)
                    # create a scope, then a collection
                    scope = self.data_manager.create_scope(
                        scope_name=self.default_scope,
                        bucket_name=bucket_size_label)

                    # Create index on scope
                    self.data_manager.create_primary_index(
                        bucket_name=bucket_size_label)

                    collection = self.data_manager.create_collection(
                        bucket_name=bucket_size_label,
                        scope_name=self.default_scope,
                        collection_name=self.default_collection)

                    # Insert (DATA_SAMPLE_SIZE times)
                    self.data_manager.run_inserts(
                        cluster_size=cluster_size,
                        bucket_name=bucket_size_label,
                        num_docs=bucket_size_value,
                        operations_to_record=self.operation_sample_size,
                        durability_level=durability_level)

                    # N1QL Query (OPERATION_SAMPLE_SIZE times)
                    self.data_manager.run_n1ql_selects(
                        cluster_size=cluster_size,
                        bucket_name=bucket_size_label,
                        operations_to_record=self.operation_sample_size,
                        durability_level=durability_level
                    )

                    # Full Text Search (.search()) (OPERATION_SAMPLE_SIZE times)
                    self.data_manager.run_full_text_searches(
                        cluster_size=cluster_size,
                        bucket_name=bucket_size_label,
                        operations_to_record=self.operation_sample_size,
                        durability_level=durability_level
                    )

                    # Update (OPERATION_SAMPLE_SIZE times)
                    self.data_manager.run_updates(
                        cluster_size=cluster_size,
                        bucket_name=bucket_size_label,
                        operations_to_record=self.operation_sample_size,
                        durability_level=durability_level
                    )

                    # Delete (OPERATION_SAMPLE_SIZE times)
                    self.data_manager.delete_docs_in_bucket(
                        cluster_size=cluster_size,
                        bucket_name=bucket_size_label,
                        operations_to_record=self.operation_sample_size,
                        durability_level=durability_level
                    )

                    # Flush bucket at the end
                    self.data_manager.flush_bucket(
                        bucket_name=bucket_size_label)

    def debug(self, msg):
        self.logger.debug(msg, extra=self.prefix)

    def info(self, msg):
        self.logger.info(msg, extra=self.prefix)

    def error(self, msg):
        self.logger.error(msg, extra=self.prefix)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='pass arguments to run various tests against a prebuilt cluster of nodes on which couchbase is already installed'
    )
    parser.add_argument('-u', '--username', help='username for managing couchbase cluster',
                        required=True)
    parser.add_argument('-p', '--password', help='password (with --username) for managing couchbase cluster',
                        required=True)
    parser.add_argument('-v', '--verbose',
                        help='increase output verbosity', action='store_true')
    parser.add_argument('-d', '--data-sample-size', help='how many documents should be in the smallest data sample? default=1000',
                        type=int, default=1000)
    parser.add_argument('-o', '--operation-sample-size',
                        help='How many operations should be executed to determine an average latency for that type of operation? default=50',
                        default=100, type=int)
    parser.add_argument('-c', '--clear-cluster', action='store_true',
                        help='Clear all the nodes out from the current cluster')
    parser.add_argument('-f', '--flush-bucket', type=str,
                        help='flush a bucket; provide bucket name to flush as argument')
    parser.add_argument('-t', '--test', action='store_true',
                        help='run the automated test framework')

    parser.add_argument('-ycsb', '--ycsb', action='store_true',
                        help='run the YCSB framework')

    parser.add_argument('-plt', '--plot', action='store_true',
                        help='generate plots from the data written to the src/lib/data directory')

    args = parser.parse_args()

    if args.flush_bucket or args.clear_cluster or args.test or args.ycsb:

        driver = Driver(args.username, args.password, args.verbose,
                        small_data_sample_size=args.data_sample_size,
                        medium_data_sample_size=args.data_sample_size * 3,
                        large_data_sample_size=args.data_sample_size * 5,
                        operation_sample_size=args.operation_sample_size,
                        default_scope="default_scope",
                        default_collection="default_collection")
        driver.get_cluster_manager().init_cluster(services=['data','index','query','fts'])

    if args.flush_bucket:
        driver.get_data_manager().flush_bucket(args.flush_bucket)
    elif args.clear_cluster:
        driver.get_cluster_manager().clear_cluster()
    elif args.test:
        # Analyze cluster size impact on performance
        driver.run_test_framework()
    elif args.ycsb:
        # Run Yahoo! Cloud Service Benchmark framework
        driver.run_ycsb()

    if args.plot:
        analyzer = Analyzer(verbose=args.verbose)
        analyzer.plot()
