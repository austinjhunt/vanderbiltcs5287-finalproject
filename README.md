# An Automated Testing Framework for Evaluating [Couchbase](https://www.couchbase.com/) as a Distributed Datastore
## An Extension of the [Vanderbilt CS 6381 Final Project]([http](https://github.com/austinjhunt/vanderbiltcs6381-finalproject))
This project is a Python-driven evaluation of [Couchbase](https://www.couchbase.com/) as a distributed datastore, completed in part as a final project for CS 6381 (Distributed Systems) at Vanderbilt University in Summer 2021 and expanded in scope as a final project for CS 5287 (Principles of Cloud Computing) at Vanderbilt University in Fall 2021, both taught by Dr. Aniruddha Gokhale.

### Tools Used
* [Ansible](https://docs.ansible.com/) for the automated provisioning and configuration of AWS EC2 infrastructure (i.e. EC2 instances)
* [Vagrant by HashiCorp](https://www.vagrantup.com/) for quickly and easily spinning up a local VirtualBox VM (using the `ubuntu/focal64` that can be used as a controller for remote cloud VMs
* [AWS EC2](https://www.vagrantup.com/) for hosting the various cloud Couchbase clusters (say *that* three times fast)
* [Couchbase-related components of the YCSB project](https://github.com/brianfrankcooper/YCSB/tree/master/couchbase2) for running automated workloads against various Couchbase databases. Using YCSB, we can fine tune variables like the ratio between read and update operations, request distributions, field counts, field sizes, and overall dataset sizes. For more information about YCSB, please read [this 2010 announcement from Yahoo! about the project.](https://research.yahoo.com/news/yahoo-cloud-serving-benchmark/)

* The [Python 3 SDK for Couchbase](https://docs.couchbase.com/python-sdk/current/hello-world/start-using-sdk.html) to programmatically adjust cluster configuration within the test scaffolding. [This article](https://docs.couchbase.com/python-sdk/2.5/managing-clusters.html) explains how the SDK can be used for cluster configuration management.
* The [Couchbase CLI](https://docs.couchbase.com/server/current/cli/cli-intro.html) to do things that cannot be done with the Python3 SDK, like much of the [Cluster Architecture Management (ClusterManager.py)](src/lib/ClusterManager.py).
* And of course, [Couchbase](https://www.couchbase.com/) as the target data store.

### Variables of Interest
We test and analyze Couchbase along a variety of metrics in an auto-provisioned cloud infrastructure environment using [AWS EC2](https://aws.amazon.com/ec2/); we analyze metrics like:
* Cluster size impact on latency of read/write/delete operations, specifically with a homogeneous architecture (same services on every node); how does adding a new node affect latency of operations?
* [Multidimensional service scaling](https://www.couchbase.com/multi-dimensional-scalability-overview) impact on read/write/delete operations; how does scaling out a service X by one additional node affect latency of read, write, update?
  * Couchbase offers [multi-dimensional scaling of services](https://docs.couchbase.com/server/6.0/clustersetup/services-mds.html), meaning that you can scale specific services independently based on what your application needs are. For example, if you are dealing with massive amounts of data, you may want to independently scale out your data service more so than the other services. [These are the main services within a Couchbase cluster.](https://docs.couchbase.com/server/current/learn/services-and-indexes/services/services.html).
* (Using YCSB) How does database size (for a given cluster size N) affect tail latency of different operation types (read/update/insert)?
  * We vary database size via variations in:
    * Document count
    * Document field count (fields per document)
    * Document field size (in bytes)
* (Using YCSB) How does a change in [request distribution](https://stackoverflow.com/questions/42767138/zipfian-vs-uniform-whats-the-difference-between-these-two-ycsb-distribution) impact tail latency of different operation types (read/update/insert)?
* (Using YCSB) How does the ratio between read/update/insert requests affect overall tail latency of database operations?



## Automation
While the [previous iteration of this project](https://github.com/austinjhunt/vanderbiltcs6381-finalproject) was mostly automated, it still required you to manually provision EC2 instances and provide their addresses to the framework before it could run. Now, we've adjusted the architecture using Vagrant and Ansible such that all you have to do is provide values of your AWS Secret Access Key and your AWS Access Key ID in a `setup-env.sh` script, and run `vagrant up --provision`. The provisioner for the Vagrant box is an Ansible Playbook that handles the **automatic provisioning and configuration** of a set of `Ubuntu 20.04` EC2 instances (particularly the installation of Couchbase), and then automatically kicks off the test framework.

The framework uses the provisioned instances to automatically and iteratively create and tear down various Couchbase cluster architectures via custom Python classes [DataManager](src/lib/DataManager.py) and [ClusterManager](src/lib/ClusterManager.py).

Python is used for not only the data management [(DataManager.py)](src/lib/DataManager.py) via the provided Python 3 SDK, but also the management of the cluster architecture in order to eliminate the need for interacting manually with the Couchbase Web GUI. Note: since much of the cluster architecture management could not be done using the default Python 3 SDK, we created methods that "wrapped" the Couchbase CLI (which *could* manage cluster architecture) to make this a fully Pythonic project.

The framework writes out data during test execution, which is used afterward to generate various plots that reveal relationships between the various variables we tune (e.g. cluster size vs. operation latency and bucket size vs. operation latency). If you want plots when the framework is done running tests, just pass `-plt` to the driver.

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
7. Copy `setup-env-template.sh` to your own environment file named `setup-env.sh` and change the environment variable values to match your environment as indicated. Your Vagrant VM will use this file to configure its environment in order to interact with AWS via Ansible.
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
This will create 5 EC2 instances (t2.xlarge) and install Couchbase on each of them automatically; it may take a little bit of time, so be patient.

12. Wait :)
13. Once tests start executing, you will be able to see data files being produced since the tests will be executing on the Vagrant VM, and that VM is mounted to the project folder. Keep an eye on the `src/lib/data` folder; that's where the raw data gets written, which is used for the plotting.
