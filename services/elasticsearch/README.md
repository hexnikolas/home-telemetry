# Elasticsearch & Kibana Logging Service

This service provides centralized log aggregation for all home-telemetry containers using Elasticsearch and Kibana.

## Overview

- **Elasticsearch:** Search and analytics engine for log storage and indexing
- **Kibana:** Web UI for searching, filtering, and visualizing logs
- **Filebeat:** Log shipper that collects JSON logs from all containers and sends them to Elasticsearch

## Quick Start

### 1. Start the Logging Stack

```bash
# Create the shared network (if not already created)
docker network create home-telemetry

# Start Elasticsearch, Kibana, and Filebeat
docker compose up -d
```

### 2. Verify Services are Running

```bash
# Check Elasticsearch health
curl http://localhost:9200/_cluster/health

# Check Kibana
open http://localhost:5601
```

### 3. Enable JSON Logging in Other Services

Each service needs to output JSON logs. Update their `.env` files:

```dotenv
# services/api/app/.env
LOG_FORMAT=json
LOG_LEVEL=DEBUG

# services/ingestion/.env
LOG_FORMAT=json
LOG_LEVEL=DEBUG

# services/jobs/.env
LOG_FORMAT=json
LOG_LEVEL=DEBUG

# services/notifier/.env
LOG_FORMAT=json
LOG_LEVEL=DEBUG
```

Or set as environment variables in their docker-compose.yml:

```yaml
environment:
  LOG_FORMAT: json
  LOG_LEVEL: DEBUG
```

### 4. Access Kibana

Open a browser to `http://localhost:5601`

## Using Kibana

### Find Your First Index

1. Go to **Management** → **Data Views** (or **Index Patterns** in older versions)
2. Click **Create Data View**
3. Index pattern: `logs-home-telemetry-*`
4. Time field: `timestamp`
5. Click **Create**

### Search Logs

Navigate to **Discover** and search:

```
# All ERROR logs
level: ERROR

# Errors in a specific service
container: home-telemetry-api AND level: ERROR

# Errors in the last hour
level: ERROR AND @timestamp: [now-1h TO now]

# Failed authentication attempts
message: "auth failed" OR message: "invalid credentials"

# Ingestion service warnings
container: home-telemetry-ingestion AND level: WARNING

# All logs from a specific function
"function": "process_observation"
```

### Create Dashboards

1. Go to **Dashboards**
2. Click **Create Dashboard**
3. Add visualizations:
   - **Error rate by service:** Count logs by container, filtered by level: ERROR
   - **Log volume over time:** Count logs, timespan chart
   - **Top error messages:** Terms on `message` field

## Log Format

Each log entry contains:

```json
{
  "timestamp": "2026-04-10T12:34:56.789Z",
  "level": "INFO",
  "service": "api",
  "logger": "app.main",
  "function": "startup",
  "line": 45,
  "message": "Application started",
  "container": "home-telemetry-api",
  "container_id": "abc123def456",
  "host": {
    "name": "myhost"
  },
  "correlation_id": "req-123",
  "request_id": "req-456",
  "user_id": "user-789",
  "extra": {
    "version": "0.1.0"
  }
}
```

### Searchable Fields

- `level` - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `service` - Service name (api, ingestion, jobs, notifier)
- `container` - Container name (home-telemetry-api, etc.)
- `message` - Log message
- `function` - Function/method name
- `line` - Line number
- `logger` - Logger name/module
- `correlation_id` - Request correlation ID
- `request_id` - Request ID
- `user_id` - User ID
- `@timestamp` - Log timestamp

## Troubleshooting

### Logs not appearing in Kibana

1. **Check Filebeat is running:**
   ```bash
   docker logs home-telemetry-filebeat
   ```

2. **Verify JSON logging is enabled:**
   ```bash
   docker logs home-telemetry-api | head -20
   # Should see JSON lines, not colored text
   ```

3. **Check Elasticsearch has data:**
   ```bash
   curl http://localhost:9200/_cat/indices
   # Should show an index like logs-home-telemetry-2026.04.10
   ```

4. **Check Filebeat can reach Elasticsearch:**
   ```bash
   docker exec home-telemetry-filebeat curl -I http://elasticsearch:9200
   ```

### High memory usage

Elasticsearch can be memory-intensive. Current settings use 512MB heap:

```yaml
"ES_JAVA_OPTS=-Xms512m -Xmx512m"
```

For development/testing, this is fine. For production, increase to 1GB-2GB.

### Old logs taking too much space

Set up index lifecycle management (ILM) to delete logs older than 30 days:

```bash
curl -X PUT "localhost:9200/_ilm/policy/logs-policy" -H 'Content-Type: application/json' -d'{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {}
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}'
```

## Docker Network

All services must be on the `home-telemetry` network. Create it once:

```bash
docker network create home-telemetry
```

Then reference it in compose files:

```yaml
networks:
  home-telemetry:
    external: true
```

## Stopping the Service

```bash
docker compose down

# Keep Elasticsearch data
docker compose down -v  # Remove volumes
```

## Production Considerations

- **Security:** `xpack.security.enabled=false` is for development only. Enable authentication for production.
- **Storage:** Elasticsearch data is persisted in `elasticsearch_data` volume. Make backups.
- **Retention:** Implement index lifecycle policies to manage storage.
- **Scaling:** Add more Elasticsearch nodes for high-volume logging.
- **Monitoring:** Monitor Elasticsearch health via `http://localhost:9200/_cluster/health`

## References

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Kibana Documentation](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Filebeat Documentation](https://www.elastic.co/guide/en/beats/filebeat/current/index.html)
