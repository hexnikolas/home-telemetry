# Redis Service

This directory contains the configuration for running a Redis instance as a service for your project.

## Usage

1. Start Redis:

   docker-compose up -d

2. Redis will be available on port 6379.

3. Data is persisted in the `redis-data` Docker volume.

## Customization

- To add a custom Redis config, place a `redis.conf` file here and uncomment the `command` line in `docker-compose.yml`.
- For advanced setups, see the [Redis documentation](https://redis.io/docs/).
