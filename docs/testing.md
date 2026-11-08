# Testing and Verification Report

## Ansible Notes Application — AWS DevOps Project

**Test environment:** AWS EC2, Amazon Linux 2023

**Automation:** Ansible

**Application:** Python Flask, Gunicorn, NGINX and SQLite

**Test date:** November 8, 2026

## 1. Testing Objectives

The purpose of these tests was to verify that the Ansible deployment correctly configures two managed EC2 instances, launches the application services, stores notes in SQLite and provides working database backups.

The tests also verify that a repeated Ansible deployment does not introduce unnecessary configuration changes.

## 2. Test Environment

| Server | Private IP | Responsibility |
|---|---|---|
| ansible-controller | 172.31.23.34 | Ansible automation |
| notes-web | 172.31.24.106 | Flask web application, Gunicorn, NGINX |
| notes-db | 172.31.27.187 | SQLite database and Flask API |

These addresses belong to the original training lab and may change if EC2 instances are recreated.

## 3. Test Results Summary

| ID | Test | Observed Result | Status |
|---|---|---|---|
| T01 | Ansible connectivity | Both hosts returned `pong` | PASS |
| T02 | Database systemd service | `active` | PASS |
| T03 | Database API health | HTTP 200, JSON status `ok` | PASS |
| T04 | Backup timer | Active, next scheduled run confirmed | PASS |
| T05 | Manual SQLite backup | Backup file created | PASS |
| T06 | SQLite backup integrity | `ok` | PASS |
| T07 | SQLite backup restore | Integrity and note count matched | PASS |
| T08 | Web application service | `active` | PASS |
| T09 | NGINX service | `active` | PASS |
| T10 | Gunicorn application endpoint | HTTP 200 | PASS |
| T11 | NGINX website endpoint | HTTP 200 | PASS |
| T12 | Public web interface | Application accessible in browser | PASS |
| T13 | Create and save a note | Successful | PASS |
| T14 | Verify note on database server | Note found in SQLite | PASS |
| T15 | Ansible web-role idempotence | `changed=0`, `failed=0` | PASS |

These results were observed during the lab execution. They are not a claim of production availability or security certification.

## 4. Ansible Connectivity Test

The controller successfully connected to both managed hosts using the inventory.

Command:

```bash
ansible all -m ansible.builtin.ping
```

Observed response:

```text
notes-web | SUCCESS
"ping": "pong"

notes-db | SUCCESS
"ping": "pong"
```

**Result:** PASS

This confirms that Ansible can connect to both hosts and execute its Python-based modules.

## 5. Database API Verification

The database API runs on `notes-db`, listening on TCP port 5051.

Command executed from the Ansible controller:

```bash
ansible database \
  -m ansible.builtin.uri \
  -a 'url=http://127.0.0.1:5051/health status_code=200'
```

Observed result:

```text
status: 200

json:
  status: ok

server: gunicorn
```

**Result:** PASS

The database API was running successfully and responding to health requests.

## 6. Database Backup Verification

The database role configures an automated SQLite backup using a systemd timer.

The timer's active state and next scheduled execution were verified.

An on-demand backup was also started:

```bash
ansible database -b \
  -m ansible.builtin.command \
  -a 'systemctl start notes-db-backup.service'
```

The resulting backup was stored under:

```text
/var/backups/notes-db/
```

The systemd journal reported successful backup creation and an SQLite integrity check of `ok`.

**Result:** PASS

### Backup restore verification

A backup file was copied to a separate temporary location and opened as an SQLite database.

The restored database was checked for integrity and compared against the original database.

Observed result at the time of this test:

```text
Live database:
  Notes: 0
  Integrity: ok

Restored database:
  Notes: 0
  Integrity: ok

RESTORE TEST PASSED
```

**Important:** This restore test was performed before the first note was saved to the deployed application. It verified a valid restoration of an initially empty database. A future test should also restore a backup containing saved notes.

## 7. Web Application Service Verification

The web server uses two services:

| Service | Purpose |
|---|---|
| `notes-web.service` | Runs the Flask application through Gunicorn |
| `nginx.service` | Provides the public HTTP endpoint |

Both services were checked using `systemctl is-active`.

Observed output:

```text
active
```

The Flask endpoint was also tested directly:

```bash
ansible web \
  -m ansible.builtin.uri \
  -a 'url=http://127.0.0.1:8080/ status_code=200'
```

Observed result: HTTP 200.

The NGINX endpoint was tested separately:

```bash
ansible web \
  -m ansible.builtin.uri \
  -a 'url=http://127.0.0.1/ status_code=200'
```

Observed result: HTTP 200.

**Result:** PASS

This confirmed that both the Python application and NGINX were responding.

## 8. End-to-End Application Test

The application was opened through the public IP address of the `notes-web` EC2 instance.

The browser displayed the Ansible Notes Application.

A new note containing the text:

```text
add my notes
```

was submitted successfully.

The application displayed a success message and showed the saved note.

The database server was then accessed separately over SSH.

A query against the SQLite database at:

```text
/var/lib/notes-db/notes.sqlite3
```

returned:

```text
Total notes: 1

ID: 1
Content: add my notes
Created: 2026-11-08T19:48:43+00:00
```

**Result:** PASS

This confirms that a note submitted through the web interface reached the separate database server and was persisted successfully.

## 9. Ansible Idempotence Test

Ansible configuration management should be idempotent: executing the same playbook repeatedly should not make unnecessary changes when the system already matches the desired configuration.

The `notes_web` role was executed again after a successful deployment.

Observed final play recap:

```text
notes-web:
  ok=17
  changed=0
  unreachable=0
  failed=0
```

**Result:** PASS

All 17 reported operations completed without requiring configuration changes.

This result verifies idempotence for the tested web-role execution. It does not establish that every possible application or infrastructure change is idempotent.

## 10. Troubleshooting — HTTP 500 Error

### Initial problem

Following the first web deployment, NGINX and Gunicorn were running but the application returned:

```text
HTTP 500 INTERNAL SERVER ERROR
```

Reviewing the Gunicorn logs revealed:

```text
jinja2.exceptions.TemplateNotFound: index.html
```

### Root cause

Flask could not locate the HTML template required to render the home page.

A search of the deployed application directory confirmed that `index.html` was missing.

### Resolution

The Ansible `notes_web` role was corrected to deploy the HTML template into:

```text
/opt/notes-web/app/templates/index.html
```

The web role was then executed again.

### Verification after correction

The deployed file was present on the managed host.

Gunicorn returned HTTP 200, and NGINX also returned HTTP 200.

**Result:** RESOLVED

This incident demonstrates the value of inspecting application logs and fixing configuration through Ansible rather than relying on undocumented manual changes.

## 11. Test Evidence

Screenshots are stored in `docs/screenshots/` when added to this repository.

Recommended evidence includes the EC2 instance overview, Ansible connectivity, database backup confirmation, successful restore, working application, persisted SQLite note and idempotence play recap.

Screenshots should be reviewed for credentials and other sensitive details before publication.

## 12. Security and Testing Limitations

The application was deployed as an educational lab.

The following areas remain outside the scope of the completed tests:

- HTTPS and public TLS certificate validation
- End-user login and authorization
- Penetration and vulnerability testing
- Load and performance testing
- Automated restore testing with nonempty database content
- High availability and disaster recovery across instances

These are recommended improvements before a production deployment.

## 13. Conclusion

The lab successfully demonstrated automated deployment of a multi-instance web application using Ansible.

Both application tiers responded correctly, data was written to the separate database server, automated SQLite backups were generated, and a backup restore test completed successfully.

The repeated web deployment also returned `changed=0`, demonstrating the desired idempotent behavior for the tested configuration.

**Overall lab result: PASS.**