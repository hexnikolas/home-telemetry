# Mosquitto MQTT Broker Container

This directory contains a container setup for running the Mosquitto MQTT broker.

## Usage Guide

1. **Create the password file**
   
   Use the Mosquitto command to generate a password file:
   
   ```sh
   mosquitto_passwd -c passwd <username>
   ```
   
   This will prompt you to enter a password for the specified user.

2. **Set file ownership**
   
   Make sure the configuration file (`mosquitto.conf`) and the password file (`passwd`) are owned by user and group `1883`:
   
   ```sh
   chown 1883:1883 mosquitto.conf passwd
   ```

3. **Change port if necessary**
   
   If you need to use a different port, edit the `mosquitto.conf` and the `docker-compose.yml` files and update the `listener` and `port` directives:
   
   ```
   listener <port>
   ports:
      - "1883:1883"
   ```

4. **Start the container**
   
   Use Docker Compose to start the broker:
   
   ```sh
   docker compose up
   ```

The broker will now be running and accessible on the configured port.