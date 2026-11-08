# Note-Taking Web Application — Ansible DevOps Project

## Objective
Deploy a Python note-taking application on AWS EC2
using reusable Ansible roles.

## Architecture
- Ansible Controller: Amazon Linux 2023
- notes-web: Flask, Gunicorn and NGINX
- notes-db: Private Python API and SQLite

## Features
- Add new notes
- Store notes with timestamps
- Display newest notes first
- Automated SQLite database backups
- Restore and recovery testing

## Automation
- Ansible inventory and configuration
- notes_web role
- notes_db role
- Repeatable deployment

## Documentation
Step-by-step implementation and verification
screenshots will be added during development.

## Project Status
Infrastructure connectivity verified.
Application development in progress.
