# Deployment Guide — Ansible Notes Application

## 1. Overview

This document explains how the Ansible Notes Application was deployed on three AWS EC2 instances using Ansible.

The deployment separates application management, the web application and database storage.

## 2. AWS Infrastructure

The lab uses Amazon Linux 2023 instances in the AWS `us-east-1` region.

| EC2 Instance | Private IP | Role |
|---|---|---|
| ansible-controller | 172.31.23.34 | Ansible automation controller |
| notes-web | 172.31.24.106 | NGINX, Gunicorn, Flask web application |
| notes-db | 172.31.27.187 | Flask database API and SQLite |

These IP addresses belong to the original lab. Replace them if recreating the infrastructure.

All three instances used the `t3.micro` instance type and the same SSH key pair for this lab.

## 3. Architecture

The Ansible controller connects to the web and database servers over SSH.

The user's browser accesses NGINX on `notes-web` using port 80.

NGINX forwards requests to the web application running on `127.0.0.1:8080`.

The web application communicates with the private database API on `notes-db` using TCP port 5051.

The database API stores notes in SQLite.

## 4. Install Ansible on the Controller

Connect to the controller using the authorized SSH key.

The following steps reproduce the original lab installation, where Ansible was installed under the root account.

```bash
sudo su

sudo dnf install -y python3.12 python3.12-pip git

python3.12 -m venv /root/ansible-venv

source /root/ansible-venv/bin/activate

python -m pip install --upgrade pip

python -m pip install ansible

ansible --version
```

The virtual environment isolates Ansible's Python packages from the operating system.

For a new production deployment, a dedicated non-root automation user is preferable.

## 5. Prepare the Project Directory

The deployment project was located at:

```text
/root/ansible-notes-project
```

The repository must contain the application code, Ansible playbook, roles, and templates.

On the controller, activate Ansible before running the commands:

```bash
cd /root/ansible-notes-project

source /root/ansible-venv/bin/activate
```

## 6. Configure SSH Access

The controller requires authorized SSH access to the two managed instances.

In the original lab, the SSH private key was stored at:

```text
/root/.ssh/ansible.pem
```

Restrict key permissions:

```bash
chmod 700 /root/.ssh
chmod 400 /root/.ssh/ansible.pem
```

Verify connectivity:

```bash
ssh -i /root/.ssh/ansible.pem ec2-user@172.31.24.106 hostname

ssh -i /root/.ssh/ansible.pem ec2-user@172.31.27.187 hostname
```

The SSH private key must never be committed to GitHub.

## 7. Create the Ansible Inventory

The original lab used a static inventory named `inventory.ini` in the controller's project directory.

```ini
[web]
notes-web ansible_host=172.31.24.106

[database]
notes-db ansible_host=172.31.27.187

[all:vars]
ansible_user=ec2-user
ansible_ssh_private_key_file=/root/.ssh/ansible.pem
ansible_python_interpreter=/usr/bin/python3
```

This inventory defines two groups:

- `web` for the application server
- `database` for the SQLite API server

The controller uses SSH as `ec2-user`, while the playbook uses privilege escalation to perform administrative tasks.

The inventory contains lab-specific host addresses and should be updated when instances are recreated.

## 8. Verify Ansible Connectivity

On the controller:

```bash
ansible-inventory -i inventory.ini --graph

ansible all -i inventory.ini -m ansible.builtin.ping
```

Expected: both managed servers return:

```text
"ping": "pong"
```

This confirms Ansible can establish connections and execute Python modules on the managed hosts.

## 9. Configure Ansible Vault

Both application components require the same private API key.

The original lab stored the encrypted variable `notes_db_api_key` in:

```text
ansible/group_vars/all/vault.yml
```

The file uses Ansible Vault encryption and a Vault ID named `lab`.

When recreating the project, generate a new secret rather than reusing an old credential.

The Vault password and decrypted API key must not be committed to Git.

The deployment playbook loads the encrypted variable file using `vars_files`.

## 10. Database Deployment Role

The `notes_db` role configures the database EC2 instance.

It performs the following operations:

- Creates a dedicated Linux service account.
- Prepares application and data directories.
- Deploys the Python database API.
- Installs Python dependencies.
- Configures the API environment file.
- Creates and enables the systemd service.
- Deploys the SQLite backup script.
- Creates a systemd backup service and timer.

The SQLite database is stored at:

```text
/var/lib/notes-db/notes.sqlite3
```

Backups are stored at:

```text
/var/backups/notes-db/
```

## 11. Web Deployment Role

The `notes_web` role configures the web EC2 instance.

It installs NGINX and Python dependencies, deploys the Flask web application, configures Gunicorn, and creates systemd services.

The application directory is:

```text
/opt/notes-web/app
```

The Flask HTML template is deployed to:

```text
/opt/notes-web/app/templates/index.html
```

NGINX listens on port 80 and proxies requests to Gunicorn on `127.0.0.1:8080`.

The application calls the database API at:

```text
http://172.31.27.187:5051
```

This is a private VPC address, not the public internet endpoint.

## 12. Run the Deployment Playbook

From the project directory on the Ansible controller:

```bash
ansible-playbook \
  -i inventory.ini \
  --syntax-check \
  --vault-id lab@prompt \
  ansible/deploy.yml
```

This checks the playbook syntax.

To deploy both servers:

```bash
ansible-playbook \
  -i inventory.ini \
  --vault-id lab@prompt \
  ansible/deploy.yml
```

The playbook configures the database server and then the web application server.

Enter the Vault password when prompted.

## 13. Verify the Database Service

```bash
ansible database -b \
  -m ansible.builtin.command \
  -a 'systemctl is-active notes-db.service'
```

Expected result:

```text
active
```

Verify the database API:

```bash
ansible database \
  -m ansible.builtin.uri \
  -a 'url=http://127.0.0.1:5051/health status_code=200'
```

Expected HTTP status: `200`.

## 14. Verify the Web Server

```bash
ansible web -b \
  -m ansible.builtin.command \
  -a 'systemctl is-active notes-web.service'
```

```bash
ansible web -b \
  -m ansible.builtin.command \
  -a 'systemctl is-active nginx.service'
```

Both services should return `active`.

Test the Flask application:

```bash
ansible web \
  -m ansible.builtin.uri \
  -a 'url=http://127.0.0.1:8080/ status_code=200'
```

Test NGINX:

```bash
ansible web \
  -m ansible.builtin.uri \
  -a 'url=http://127.0.0.1/ status_code=200'
```

Both returned HTTP 200 during the lab.

## 15. Verify Database Backups

Run an on-demand backup:

```bash
ansible database -b \
  -m ansible.builtin.command \
  -a 'systemctl start notes-db-backup.service'
```

Inspect the backup directory:

```bash
ansible database -b \
  -m ansible.builtin.command \
  -a 'ls -lh /var/backups/notes-db/'
```

The lab successfully created an SQLite backup and verified its integrity.

The scheduled backup timer was also confirmed active.

## 16. Test Idempotence

Rerun the deployment without changing configuration:

```bash
ansible-playbook \
  -i inventory.ini \
  --limit notes-web \
  --vault-id lab@prompt \
  ansible/deploy.yml
```

The web role's second deployment completed with:

```text
ok=17 changed=0 unreachable=0 failed=0
```

This confirms the web role did not make unnecessary changes during the repeated run.

## 17. Security Notes

This deployment was built as a learning project.

The original lab used a shared AWS Security Group. A production deployment should restrict inbound rules appropriately, particularly SSH and the database API port.

Additional production improvements include:

- HTTPS/TLS for the public website
- End-user authentication
- Non-root Ansible execution
- Restricting SSH to trusted sources
- Limiting port 5051 access to the web application server
- Centralized logging and monitoring
- Secure application secret management
- Removing unnecessary public IP addresses

The SQLite database file, SSH keys, plaintext secrets and local virtual environments must never be published to GitHub.

## 18. Conclusion

The Ansible deployment successfully configured the web and database tiers, managed systemd services, deployed the application, tested HTTP connectivity, verified SQLite data persistence, and automated database backups.

The deployment was also tested for web-role idempotence, returning `changed=0` on a repeated execution.
