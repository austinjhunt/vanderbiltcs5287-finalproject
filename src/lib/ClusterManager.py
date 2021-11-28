""" Class responsible for managing a couchbase cluster. Primarily uses the subprocess library to execute
couchbase-cli commands to interact with cluster configuration. You must have couchbase-cli installed on your system for this to work. """

import logging
import subprocess
import json
import os
import random
from couchbase.cluster import UserManager
from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.management.users import User, Role

class ClusterManager:
    def __init__(self, username, password, verbose):
        self.username = username
        self.password = password
        self.hosts = self.get_hosts_from_json()
        self.randomly_assign_host_roles() # assigns self.leader, self.followers randomly
        # Use the public IP of leader for couchbase url endpoint
        self.couchbase_url = f'couchbase://{self.get_public_address(self.leader)}'
        # Logging
        self.setup_logging(verbose)

        self.logger.info(f'Couchbase Endpoint URL (using leader public IP): {self.couchbase_url}')
        self.logger.info('Available Hosts:')
        self.logger.info(f'Leader: {self.leader}')
        self.logger.info(f'Followers: {self.followers}')

    def get_password(self):
        return self.password


    def get_leader_address(self):
        return self.get_public_address(self.leader)

    def get_cluster_url(self, protocol='couchbase'):
        # protocol can be either http or couchbase
        return self.couchbase_url if protocol == 'couchbase' else self.couchbase_url.replace('couchbase://','http://')

    def get_max_cluster_size(self):
        """ return the maximum cluster size (# available hosts) """
        return len(self.hosts)

    def setup_logging(self, verbose):
        """ set up self.logger for Driver logging """
        self.logger = logging.getLogger('ClusterManager')
        formatter = logging.Formatter('%(prefix)s - %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.prefix = {'prefix': 'Cluster Manager'}
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

    def remove_node_from_cluster(self, node_private_address="", node_dns_name=""):
        """ Pass in an address of a cluster node to remove it """
        addr = node_private_address if node_private_address else node_dns_name
        remove_node_cmd = (
            f'couchbase-cli rebalance -c {self.couchbase_url} --username {self.username} '
            f'--password {self.password} --server-remove {addr}'
        )
        process = subprocess.Popen(remove_node_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        if error and error != "None":
            self.error(error)
        self.info(output)

    def graceful_failover_node(self, node_private_address="", node_dns_name=""):
        """ Perform a graceful failover of a node """
        addr = node_private_address if node_private_address else node_dns_name
        graceful_failover_cmd = (
            f'couchbase-cli failover -c {self.couchbase_url} --username {self.username} '
            f'--password {self.password} --server-failover {addr}'
        )
        process = subprocess.Popen(graceful_failover_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        if error and error != "None":
            self.error(error)
        self.logger.info(output)

    def _add_public_alt_addr(self, node):
        """ Add public IP address as alt address for a given node in cluster """
        cmd = (
            f'couchbase-cli setting-alternate-address '
            f'--cluster {self.get_public_address(node)}:8091 '
            f'--node {self.get_dns_name(node)} '
            f'--username {self.username} '
            f'--password {self.password} '
            f'--set '
            f'--hostname {self.get_dns_name(node)} '
        )
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        if error and error != "None":
            self.error(error)
        if output and output != "None":
            self.info(output)

    def add_alternate_couchbase_addresses(self):
        """ Add the public IP address as the alternate address for each node in the cluster.
        Couchbase tends toward using private which prevents the SDK from working properly.
        """
        self.info("Adding public address as alternate address for each cluster node")
        # Leader first
        self._add_public_alt_addr(self.leader)
        # Now followers
        for f in self.followers:
            self._add_public_alt_addr(f)

    def add_node_to_cluster(self, node_private_address="", node_dns_name="", services="data"):
        """ Given an address of a node within a VPC, add that node to a cluster by
        passing it to the leader of the cluster with the server-add command. Indicate what services it should run! Options: "data", "index", "query", "fts" (full text search), "eventing", "analytics" and "backup". Don't use analytics, eventing, or backup for this testing. """

        addr = node_private_address if node_private_address else node_dns_name
        self.logger.info(f"Adding node (addr={addr}) to cluster")
        add_node_cmd = (
            f'couchbase-cli server-add '
            f'--cluster {self.couchbase_url} '
            f'--server-add http://{addr}:8091 '
            f'--username {self.username} '
            f'--password {self.password} '
            f'--server-add-username {self.username} '
            f'--server-add-password {self.password} '
            f'--services {services}'
        )
        process = subprocess.Popen(add_node_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        self.logger.info(output)
        if error and error != "None":
            self.error(error)

    def get_hosts_from_json(self):
        hosts_file = f'{os.path.dirname(os.path.abspath(__file__))}/hosts.json'
        hosts = []
        try:
            with open(hosts_file) as f:
                hosts = json.load(f)['hosts']
        except Exception as e:
            print(e)
        return hosts

    def randomly_assign_host_roles(self):
        """ Randomly select one of self.hosts as leader, rest as followers """
        self.leader = self.hosts[0]
        self.followers = [el for el in self.hosts if el != self.leader]

    def get_leader(self):
        return self.leader

    def get_followers(self):
        return self.followers

    def get_public_address(self,host):
        return host['public']

    def get_private_address(self, host):
        return host['private']

    def get_dns_name(self, host):
        return host['dns']

    def fix_leader_address(self):
        """
        When you initialize a cluster, even if you use the public DNS name
        of the leader, the node ends up using its private IP address. So,
        remove the leader node and re-add it using its public DNS name. """
        self.info("Configuring the leader to use its public DNS name as its node address")
        # ASSUMPTION: THERE IS MORE THAN ONE NODE AVAILABLE
        self.leader = self.hosts[1]
        self.couchbase_url = f'couchbase://{self.get_dns_name(self.leader)}'
        # original leader currently stuck with its private IP so use that address to remove it
        self.remove_node_from_cluster(
                node_private_address=
                    self.get_private_address(self.hosts[0])) # remove original leader
        self.rebalance_cluster()
        self.add_node_to_cluster(node_dns_name=self.get_dns_name(self.hosts[0])) # re-add original leader
        self.rebalance_cluster()
        # now re-set the couchbase endpoint to the original leader
        self.leader = self.hosts[0]
        self.couchbase_url = f'couchbase://{self.get_dns_name(self.leader)}'

    def init_cluster(self, services=['data']):
        """ Initialize a couchbase cluster (use the public IP of a host randomly selected to be leader);
        optionally pass in a list of services to start on the first node of the cluster; default is just data,
        but you may also run index, query, fts (we are ignoring eventing, analytics and backup) """
        services = ",".join(services)
        init_cluster_cmd = (
            f'couchbase-cli cluster-init '
            f'-c {self.couchbase_url} '
            f'--cluster-username {self.username} '
            f'--cluster-password {self.password} '
            f'--services {services}'
        )
        process = subprocess.Popen(init_cluster_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        self.info(output.decode())
        if error and error != "None":
            self.error(error)

    def rebalance_cluster(self):
        """ Rebalance a cluster (after adding a node; important) """
        self.info("Rebalancing cluster")
        rebalance_cmd = (
            f'couchbase-cli rebalance '
            f'-c {self.couchbase_url} '
            f'--username {self.username} '
            f'--password {self.password} '
        )
        process = subprocess.Popen(rebalance_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        if error and error != "None":
            self.error(error)
        if output and output != "None":
            self.info(output)

    def get_service_layouts(self):
        """ Build an array of service layouts. Each layout is a map of what services run on what hosts for a given test round. NEED at least 5 hosts. Service options: "data", "index", "query", "fts". Each layout is a dictionary with key = host index, value = {'services': CSV service list, 'host': host object }. SKIP leader. Leader can always run data service."""
        service_layouts = []
        # Co-located
        layout = {}
        hosts = self.hosts.copy()
        hosts.remove(self.leader)
        for index, host in enumerate(hosts):
            # All hosts running same services
            layout[index] = {"services": "data,index,query,fts", "host": host}
        service_layouts.append(layout)

        # Add service layouts to measure impact of specific services being scaled
        for service in ["data", "fts", "query", "index"]:
            service_layouts.extend(
                self.build_service_layouts_to_measure_specific_service_impact(service=service)
            )
        return service_layouts

    def clear_cluster(self):
        """ Remove all nodes from cluster aside from leader (only followers) """
        self.info("clearing cluster...")
        for follower in self.get_followers():
            self.info(f"removing node {self.get_dns_name(follower)}")
            self.remove_node_from_cluster(node_dns_name=self.get_dns_name(follower))

    def build_service_layouts_to_measure_specific_service_impact(self, service="data"):
        """ Measure impact of multidimensional scaling for specific service.
        Run ONLY this service on one node, then on two, then three. Use
        co-located services for the remaining hosts. """
        # ONLY X service on 1 node, everything else co-located
        service_layouts = []
        layout = {}
        layout[0] = service
        hosts = self.hosts.copy()
        hosts.remove(self.leader)
        for index, host in enumerate(hosts):
            layout[index] = {"services": "data,index,query,fts", "host": host}
        service_layouts.append(layout)

        # ONLY X service on 2 nodes, everything else co-located
        layout = {}
        layout[0] = service
        layout[1] = service
        for index, host in enumerate(hosts):
            layout[index] = {"services": "data,index,query,fts", "host": host}
        service_layouts.append(layout)

        # ONLY X service on 3 nodes, everything else co-located
        layout = {}
        layout[0] = service
        layout[1] = service
        layout[2] = service
        for index, host in enumerate(hosts):
            layout[index] = {"services": "data,index,query,fts", "host": host}
        service_layouts.append(layout)
        return service_layouts

    def setup_cluster_with_service_layout(self, service_layout):
        """ Given a service layout/service map (which services running on which hosts?),
        set up a new cluster. Assume cluster already clear. service_layout structure:
        {
            0 (host index) : {
                "services" : "[data,query,index,fts]",
                "host": {
                    "public": <public IP>,
                    "private": <private IP>,
                    "dns": <public DNS>
                    }
                }
            },
            1 (next host index) : { .... }
        }

         """
        self.debug(f"Creating a cluster with service layout {service_layout}")
        for host_index in service_layout:
            # For each non-leader-host
            services = service_layout[host_index]["services"]
            host_dns_name = service_layout[host_index]["host"]["dns"]
            self.add_node_to_cluster(node_dns_name=host_dns_name, services=services)
        # Rebalance after adding all nodes based on layout
        self.rebalance_cluster()

    def create_admin_user(self, username, password):
        self.info(
            f"Creating user with username {username} and password {password} "
            f"with role admin using couchbase URL "
            f"{self.couchbase_url}")
        cluster = Cluster(
            self.couchbase_url,
            authenticator=PasswordAuthenticator(
                self.username,
                self.password
            ))
        user_manager = cluster.users()
        self.debug(f"Cluster: {cluster}")
        self.debug(f"User Manager: {user_manager}")
        user = User(
                username=username,
                password=password,
                display_name=username,
                roles=[ Role(name="admin") ]
            )
        self.info(f"Upserting user: {user}")
        response = user_manager.upsert_user(user)
        self.info(response)

    def create_user_for_bucket(self, username="", password="", bucket_name=""):
        """ Create a user in couchbase cluster """
        # Add user to cluster via Python API

        self.info(
            f"Creating user with username {username} and password {password} "
            f"with role bucket_full_access on bucket=* using couchbase URL "
            f"{self.couchbase_url}")
        cluster = Cluster(
            self.couchbase_url,
            authenticator=PasswordAuthenticator(
                self.username,
                self.password
            ))
        user_manager = cluster.users()
        self.debug(f"Cluster: {cluster}")
        self.debug(f"User Manager: {user_manager}")
        user = User(
                username=username,
                password=password,
                display_name=username,
                roles=[
                    # Roles required for reading data from bucket
                    Role(name="bucket_full_access", bucket=bucket_name)
                ]
            )
        self.info(f"Upserting user: {user}")
        response = user_manager.upsert_user(user)
        self.info(response)


    def setup_cluster_colocated_services(self,cluster_size=0): #, using_ycsb=False):
        """ Create a cluster of size N with co-located services. """
        services = "data,query,index,fts"
        self.info(f"Creating cluster (co-located services) of size {cluster_size + 1} nodes")
        for index, follower in enumerate(self.followers):
            if index < cluster_size:
                host_dns_name = self.get_dns_name(follower)
                self.add_node_to_cluster(node_dns_name=host_dns_name, services=services)
        # Rebalance after adding all nodes based on layout
        self.rebalance_cluster()
        # Enable access via public IP; breaks for YCSB
        self.add_alternate_couchbase_addresses()
