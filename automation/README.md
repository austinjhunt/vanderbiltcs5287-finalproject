# Ansible
Test Commands:
```
ansible chameleon -u cc -m ping  -i hosts.ini --private-key ../.ssh/ajh-cc-keypair.pem
ansible chameleon -a "/bin/echo hello world" -i hosts.ini -u cc --private-key ../.ssh/ajh-cc-keypair.pem```