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

The notifier is implemented as a Python script. It connects to a Redis instance and subscribes to the `observations:global` channel to receive real-time updates from other services.

## Redis Integration

The service uses Redis Pub/Sub to listen for new observation events. When a message is published to `observations:global`, the notifier processes the event and determines if a notification should be sent.

## Gotify Notifications

Notifications are delivered using Gotify, a simple server for sending push notifications. The notifier sends HTTP requests to the Gotify server with the relevant alert information, allowing users to receive timely updates on their devices.