# Database Containers Guide

This directory contains a Docker Compose setup for running TimescaleDB and pgAdmin containers.

## Usage

> **Note:** Execute all commands below from the directory of this README file.

1. **Prepare Data Directories**
   
   Create the required directories for persistent data storage (relative to this folder):
   
   ```sh
   mkdir -p ./data/timescaledb
   mkdir -p ./data/pgadmin
   ```

2. **Set Permissions**
   
   Ensure the directories have the correct ownership for the containers:
   
   ```sh
   sudo chown -R 70:70 ./data/timescaledb
   sudo chown -R 5050:5050 ./data/pgadmin
   ```

3. **Start the Containers**
   
   Launch the database containers using Docker Compose:
   
   ```sh
   docker compose up
   ```

---

Your TimescaleDB and pgAdmin services will now be running and ready for use. Adjust relative paths and permissions as needed for your environment.
