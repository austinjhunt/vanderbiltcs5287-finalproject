#!/bin/bash
# Script to set up your environment variables. Run this before executing ansible playbooks/vagrant.
export AWS_ACCESS_KEY_ID="CHANGEME"
export AWS_SECRET_ACCESS_KEY="CHANGEME"

# Reference: https://docs.couchbase.com/server/current/cli/cli-intro.html
export PATH=$PATH:*** PATH TO COUCHBASE BIN FOLDER ON YOUR OS ***

# Leave this
export PATH=$PATH:$(pwd)/ycsb/bin