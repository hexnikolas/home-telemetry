# Grafana Container Guide

This directory contains a Docker setup for running Grafana for data visualization.

## Usage

1. **Start Grafana**
   
   Use Docker Compose to bring up the Grafana container:
   
   ```sh
   docker compose up
   ```

2. **Login**
   
   Open your browser and go to `http://localhost:3000` (or the configured port).
   
   Log in with the default credentials:
   - **Username:** admin
   - **Password:** admin

3. **Add Database Connection**
   
   After logging in, add a new data source (e.g., PostgreSQL, TimescaleDB, etc.) to connect Grafana to your database.

4. **Create Panels**
   
   Create dashboards and panels to visualize your data as needed.

5. **My Setup**
      
   ![Your Grafana Dashboard](https://imgur.com/a/pDe2fOd)

