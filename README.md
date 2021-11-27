# An Automated Testing Framework for Evaluating [Couchbase](https://www.couchbase.com/) as a Distributed Datastore
## An Extension of the [Vanderbilt CS 6381 Final Project]([http](https://github.com/austinjhunt/vanderbiltcs6381-finalproject))
This project is a Python-driven evaluation of [Couchbase](https://www.couchbase.com/) as a distributed datastore, completed in part as a final project for CS 6381 (Distributed Systems) at Vanderbilt University in Summer 2021 and expanded in scope as a final project for CS 5287 (Principles of Cloud Computing) at Vanderbilt University in Fall 2021.

Specifically, we test and analyze Couchbase along a variety of metrics in an auto-provisioned cloud infrastructure environment using [AWS EC2](https://aws.amazon.com/ec2/); we analyze metrics like:
- Cluster size impact on latency of read/write/delete operations, specifically with co-located services (same services on every node); how does adding a new node affect latency of operations?
- [Multidimensional service scaling](https://www.couchbase.com/multi-dimensional-scalability-overview) impact on read/write/delete operations; how does scaling out a query service by one additional node affect query latency?
  - Couchbase offers multi-dimensional scaling of services, meaning that you can scale specific services independently based on what your application needs are. For example, if you are dealing with massive amounts of data, you may want to independently scale out your data service more so than the other services. [These are the main services within a Couchbase cluster.](https://docs.couchbase.com/server/current/learn/services-and-indexes/services/services.html).
- Latency of the [DCP (Database Change Protocol)](https://docs.couchbase.com/server/current/learn/clusters-and-availability/intra-cluster-replication.html#database-change-protocol) (high performance protocol for replicating each atomic document write to every node in the cluster) as it relates to:
  - Size of write operation
  - Size of cluster
  - Quorum failure
- Node failover impact on data operation latency - how does the latency of read/write/delete change during a node failover within a cluster? It should only affect the operations which map to that specific node being failed over ([this is why](https://docs.couchbase.com/server/5.0/architecture/core-data-access-vbuckets-bucket-partition.html) - vBucket partitioning)
  - Also, what is the average time for a node to fail over? Is it different for graceful and hard failovers?
- How does data size (for a given cluster size N) affect query performance? Answer by:
  - For cluster size 1...5
    - For data size small....large
      - Capture average read latency
      - Capture average write latency
      - Capture average delete latency
- How does network partitioning/node failure affect latency of cluster metadata changes? Answer by:
  - Capture tail latency of metadata change command for a fully working cluster (without changing cluster size, change some other part of config, e.g. permissions, service layout, etc.)
  - Kill some number of nodes less than quorum, capture average latency again
  - Kill some number of nodes >= quorum, capture average latency again - this should not succeed / commit until quorum recovers.
- How does dataset size (using YCSB) affect tail latency of different data operations (read/write)?
- How does [request distribution](https://stackoverflow.com/questions/42767138/zipfian-vs-uniform-whats-the-difference-between-these-two-ycsb-distribution) (using YCSB) impact tail latency of data operations?
  - We'll be looking at **uniform** and **zipfian** request distributions, defined respectively as:
    - Uniform: each row has an equal probability to be read
    - Zipfian: some rows have more probability to be targeted by reads or scans; those rows are called "hot set" or "hot spot" and represent popular data, for instance popular threads of a forum.
- How does the ratio between read and write requests (using YCSB) affect overall tail latency of database operations?

## Tools Used
- This project uses the [Python 3 SDK for Couchbase](https://docs.couchbase.com/python-sdk/current/hello-world/start-using-sdk.html) to programmatically adjust cluster configuration within the test scaffolding. [This article](https://docs.couchbase.com/python-sdk/2.5/managing-clusters.html) explains how the SDK can be used for cluster configuration management.
- It also uses the [Couchbase CLI](https://docs.couchbase.com/server/current/cli/cli-intro.html) to do things that cannot be done with the Python3 SDK, like much of the [Cluster Architecture Management (ClusterManager.py)](src/lib/ClusterManager.py).
- It uses a subset of the [Yahoo! Cloud Serving Benchmark](https://github.com/brianfrankcooper/YCSB/tree/master/couchbase2) project for automated load testing against the Couchbase cluster.
- It uses [Vagrant by HashiCorp](https://www.vagrantup.com/) for quickly and easily spinning up a local VirtualBox VM (using the `ubuntu/focal64` that can be used as a controller for remote cloud VMs
- It uses [Ansible](https://docs.ansible.com/) for the automated provisioning and configuration of AWS EC2 infrastructure (i.e. EC2 instances)

## Automation
While the [previous iteration of this project](https://github.com/austinjhunt/vanderbiltcs6381-finalproject) was mostly automated, it still required you to manually provision EC2 instances and provide their addresses to the framework before it could run. Now, we've adjusted the architecture using Vagrant and Ansible such that all you have to do is provide values of your AWS Secret Access Key and your AWS Access Key ID in a `setup-env.sh` script, and run `vagrant up --provision`. The provisioner for the Vagrant box is an Ansible Playbook that handles the automatic provisioning and configuration of a set of `Ubuntu 20.04` EC2 instances (particularly the installation of Couchbase), and then automatically kicks off the test framework.

The framework uses the provisioned instances to automatically and iteratively create and tear down various Couchbase cluster architectures.

Python is used for not only the data management [(DataManager.py)](src/lib/DataManager.py) via the provided Python 3 SDK, but also the management of the cluster architecture in order to eliminate the need for interacting manually with the Couchbase Web GUI. Note: since much of the cluster architecture management could not be done using the default Python 3 SDK, we created methods that "wrapped" the Couchbase CLI (which *could* manage cluster architecture) to make this a fully Pythonic project.

The framework writes out data during test execution, which is used afterward to generate various plots that reveal relationships between the various variables we tune (e.g. cluster size vs. operation latency and bucket size vs. operation latency).

### Testing Approach
#### Test Multidimensional Scaling Impact on Operation Latencies
1. 5 total servers/nodes available to test with.
2. Let `SERVICE_LAYOUTS` describe:
   1. co-located: same services on every node
   2. ONLY data service on 1/5 node, everything else co-located
   3. ONLY data service on 2/5 nodes, everything else co-located
   4. ONLY data service on 3/5 nodes, everything else co-located
   5. ONLY index service on 1/5 node, everything else co-located
   6. ONLY index service on 2/5 nodes, everything else co-located
   7. ONLY index service on 3/5 nodes, everything else co-located
   8. ONLY query service on 1/5 node, everything else co-located
   9. ONLY query service on 2/5 nodes, everything else co-located
   10. ONLY query service on 3/5 nodes, everything else co-located
   11. ONLY search service on 1/5 node, everything else co-located
   9. ONLY search service on 2/5 nodes, everything else co-located
   10. ONLY search service on 3/5 nodes, everything else co-located
   12. **NOTE: This will reveal the impact on performance of multi-dimensional scaling of each service. We are not testing with [Eventing](https://docs.couchbase.com/server/current/learn/services-and-indexes/services/eventing-service.html), [Backups](https://docs.couchbase.com/server/current/learn/services-and-indexes/services/backup-service.html), or [Analytics](https://docs.couchbase.com/server/current/learn/services-and-indexes/services/analytics-service.html) so those are left out of the service layouts.**
3. For `service_layout` in `SERVICE_LAYOUTS`
   1. Create a cluster of 5 nodes with this service layout.
      1. For `bucket_size` in [SMALL=DATA_SAMPLE_SIZE,MEDIUM=DATA_SAMPLE_SIZE*2.5,LARGE=DATA_SAMPLE_SIZE*5]
         1. Create bucket. Run operations. Collect latencies.
4. Let `DATA_SAMPLE_SIZE=1000`
5. Let `OPERATION_SAMPLE_SIZE=100`

#### Test Durability Impact on Operation Latency, Cluster Size Impact on Operation Latency, and Bucket Size Impact on Operation Latency within One Loop (for multiple operation types)
1. For `durability_level` in low, medium, high:
   1. For `cluster_size` in 1...5
   2. Spin up a single Couchbase cluster of size `cluster_size`
      1. For `bucket_size` in [SMALL=DATA_SAMPLE_SIZE,MEDIUM=DATA_SAMPLE_SIZE*2.5,LARGE=DATA_SAMPLE_SIZE*5] (** the specific thresholds are not important here, but will each represent a specific number of documents)
         1. Create a bucket.
         2. Insert `bucket_size` documents to it. Use `OPERATION_SAMPLE_SIZE` of those inserts to calculate average latency. Write to file.
         3. Perform `OPERATION_SAMPLE_SIZE` read operations. Calculate average latency. Write to file.
            1. For j = 1..5:
               1. Perform `OPERATION_SAMPLE_SIZE` read operations again, but this time do a graceful failover of one of the nodes during the loop to see how latency is affected. Write to file.
         4. Perform `OPERATION_SAMPLE_SIZE` update operations. Calculate average latency.
            1. For j = 1..5:
               1. Perform `OPERATION_SAMPLE_SIZE` update operations again, but this time do a graceful failover of one of the nodes during the loop to see how latency is affected. Write to file.
         5. Perform `OPERATION_SAMPLE_SIZE` delete operations. Calculate average latency. **Note**: SMALL must be greater than number of delete operations.
            1. For j = 1..5:
               1. Restore the deleted data, then
               2. Perform `SAMPLE_SIZE` delete operations again, but this time do a graceful failover of one of the nodes during the loop to see how latency is affected. Write to file.
## Terminology
### [Scopes & Collections](https://docs.couchbase.com/server/current/learn/data/scopes-and-collections.html)
A *collection* is a data container, defined on Couchbase Server, within a bucket whose type is either Couchbase or Ephemeral. Up to 1000 collections can be created per cluster.
A *scope* is a mechanism for the grouping of multiple collections. Up to 1000 scopes can be created per cluster.

### [Primary Indexes](https://docs.couchbase.com/server/current/learn/services-and-indexes/indexes/global-secondary-indexes.html)
Primary indexes and Global Secondary Indexes (GSI) support queries made by the `query` service by providing predictable performance, low latency querying, and more. For this framework, we create a default primary index for each bucket we create that can be searched against during the Full Text Search query test.

## Development Environment - Getting Started
To work with the project, do the following:
1. Clone the repository
```
git clone https://github.com/austinjhunt/vanderbiltcs6381-finalproject.git
```
2. [Install Python 3.8](https://www.python.org/downloads/release/python-380/) if not already installed.
4. Navigate into the project (`cd vanderbiltcs6381-finalproject`) and create a Python 3.8 virtual environment, then activate it.
```
python3.8 -m venv venv && source venv/bin/activate
```
5. [Install Couchbase locally.](https://docs.couchbase.com/python-sdk/2.5/start-using-sdk.html#installing-on-mac-os-x). Follow the linked directions matching your operating system.
6. [Make sure Couchbase CLI is included in your PATH](https://docs.couchbase.com/server/current/cli/cli-intro.html).
7. Copy `setup-env-template.sh` to your own `setup-env.sh` and change the environment variable values to match your environment.
8. Activate your environment variables with `source setup-env.sh`
9. Install the Python requirements:
```
pip install -r requirements.txt
```
10. Install [Vagrant](https://www.vagrantup.com/docs/installation).
11.  Create a Vagrant box and provision it using the master playbook included in the automation directory. Simply run `vagrant up --provision` from the `automation` folder.
```
cd automation
vagrant up --provision
```
This will create 5 EC2 instances (t2.medium) and install Couchbase on each of them automatically; it may take a little bit of time, so be patient.
12.  Run the `setup.py` script: `python setup.py`
13.  Run the setup script with `python setup.py -p`.  This script will set up a [src/lib/hosts.json](src/lib/hosts.json) file containing a map of the public and private IP addresses (paired) of each of your EC2 hosts in JSON format. The framework depends on this for automatic cluster management.


## [YCSB (Yahoo! Cloud Serving Benchmark)](https://github.com/brianfrankcooper/YCSB)
We use the [couchbase-related components of the YCSB project](https://github.com/brianfrankcooper/YCSB/tree/master/couchbase2) to run automated workloads against our created database. Using YCSB, we can fine tune variables like the ratio between read and update operations, request distributions, field counts, field sizes, and overall dataset sizes.
For more information about YCSB, please read [this 2010 announcement from Yahoo! about the project.](https://research.yahoo.com/news/yahoo-cloud-serving-benchmark/)

## Running the Framework
1. Navigate to the [src](src/__init__.py) directory
```
cd src
```
2. Run the following command to execute the framework.
```
python driver.py -u <desired couchbase username> -p <desired couchbase password> -v -t -plt
```
3. Wait :) The above command will automatically provision various cluster topologies, run tests with verbose output, write organized latency data to [src/lib/data](src/lib/data), and generate various plots based on that data in [src/lib/plots](src/lib/pltos).