# Notifier Service

This service handles sending notifications for the home telemetry system. It listens for events and delivers alerts via configured channels. Simple setup, easy integration.

## Getting Started

1. Start the service using Docker Compose:

    ```sh
    docker-compose up
    ```

2. Open your browser and go to [http://localhost:9090](http://localhost:9090).

3. Create a new application in Gotify and copy the generated app key.

4. Paste the app key into the `.env` file under the appropriate variable.

5. Log in to the Gotify mobile app using the same user account you used to create the application.

## Notification Rules

Notification rules define which events trigger alerts and how they are delivered. You can configure rules to filter specific types of observations, set thresholds, or customize notification channels. This allows for flexible and targeted alerting based on your needs.

## Python Script

The notifier is implemented as a Python script. It connects to a Redis instance and subscribes to specific `datastream:{uuid}` streams for datastreams configured in the rules to receive real-time observation updates from the API.

## Redis Integration

The service uses Redis Streams to listen for new observation events. For each datastream configured in `rules.yaml`, the notifier subscribes to its dedicated `datastream:{uuid}` stream using consumer groups. This targeted approach reduces Redis load by only monitoring relevant datastreams instead of all observations.

When observations are published to monitored datastream streams, the notifier:
- Updates heartbeat tracking (last-seen timestamps) to detect offline sensors
- Evaluates threshold rules to trigger alerts when values exceed configured limits

## System Monitoring

The notifier provides comprehensive system health monitoring:

### Observation Monitoring
- **Threshold alerts**: Notifies when sensor values exceed configured limits (e.g., high temperature, power usage)
- **Heartbeat monitoring**: Detects offline sensors when no data received within timeout period

### Infrastructure Monitoring
- **RabbitMQ queue depth**: Alerts when message queue grows beyond threshold (potential backlog)
- **Dead Letter Queue (DLQ)**: Alerts when messages fail permanently and move to DLQ (data quality issues)
- **Docker container health**: Monitors container health status changes
- **Redis connectivity**: Tracks Redis availability and recovery

All monitoring rules are configured in `rules.yaml` with customizable thresholds, priorities, and cooldown periods.

## Gotify Notifications

Notifications are delivered using Gotify, a simple server for sending push notifications. The notifier sends HTTP requests to the Gotify server with the relevant alert information, allowing users to receive timely updates on their devices.