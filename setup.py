""" Execute this module to 1) (optionally) automatically install Couchbase on your EC2 hosts, and 2) create a necessary hosts.json file containing the public and private IP addresses of your hosts """
import subprocess
import configparser
import json
import argparse
import os
import boto3

from src.lib.RandomDocumentGenerator import RandomDocumentGenerator

class Setup:
    def __init__(self):
        self.ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID', ''),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY',''))

    def get_ec2_instance_addresses(self):
        """ return list of dicts {'public_ip': '', 'private_ip': ''} corresponding to each ec2 instance"""
        response = self.ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'instance.group-name',
                    'Values': ['cs5287final-security-group']
                }
            ]
        )
        addresses = []
        if 'Reservations' in response:
            for r in response['Reservations']:
                instances = r['Instances']
                for i in instances:
                    addresses.append({
                        'public': i['PublicIpAddress'],
                        'private': i['PrivateIpAddress']
                    })
        return addresses

    def run_ansible_playbook(self):
        """ Run ansible playbook to install and start couchbase on provided hosts (public_addresses) """
        # Run the ansible playbook to install couchbase on the hosts in the hosts.ini file
        playbook_cmd = "ansible-playbook -i hosts.ini playbook.yml"
        # silence the "Are you sure you want to continue connecting? (yes/no)" prompt using environment var
        os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
        print(f'Running playbook with ansible: `{playbook_cmd}`')
        process = subprocess.Popen(playbook_cmd.split())
        output, error = process.communicate()
        if error:
            print('Error? ' + error)
        print(output)


    def build_hosts_json_file(self):
        """ Use the top level hosts.ini file to generate a hosts.json file for the framework to use """
        hosts = {
            'hosts': setup.get_ec2_instance_addresses()
        }
        with open('src/lib/hosts.json','w') as f:
            json.dump(hosts, f)
        print('Successfully built src/lib/hosts.json!')

    def build_test_data_sample(self):
        """ Populate the src/lib/random_docs with randomized JSON documents """
        gen = RandomDocumentGenerator(verbose=False)
        gen.generate_random_docs(num_docs=5000, doc_size=50, key_size=30, value_size=30)

if __name__ == "__main__":
    setup = Setup()
    setup.build_hosts_json_file()
    setup.build_test_data_sample()