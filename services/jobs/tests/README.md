# Jobs Service Tests

Comprehensive test suite for the Dramatiq-based jobs service.

## Running Tests

### All tests
```bash
pytest
```

### Specific test file
```bash
pytest tests/test_tasks.py
pytest tests/test_scheduler.py
pytest tests/test_broker.py
```

### Specific test class
```bash
pytest tests/test_tasks.py::TestFetchOpenMeteoData
```

### Specific test
```bash
pytest tests/test_tasks.py::TestFetchOpenMeteoData::test_fetch_current_data_first_run
```

### With verbose output
```bash
pytest -v
```

### With coverage
```bash
pytest --cov=app tests/
```

## Test Coverage

### test_tasks.py
Tests for Dramatiq task actors:
- **TestFetchOpenMeteoData**: Open Meteo API integration
  - First run (current data fetch)
  - Retry runs (historical data fetch)
  - Error handling (system not found, no datastreams)
  - Hourly data extraction
  - Partial observations
  - API errors
  - Result time preservation
  - Bulk observation creation

- **TestSyncMqttTopics**: MQTT topic synchronization
- **TestTrainTemperatureModel**: Temperature model training with Prophet
- **TestTaskActorConfiguration**: Verify Dramatiq actor setup

### test_scheduler.py
Tests for APScheduler configuration:
- Scheduler initialization
- Job registration (MQTT, Open Meteo, Temperature Model)
- Cron trigger schedules
  - MQTT: every 5 minutes
  - Open Meteo: at :00 and :30 each hour
  - Temperature Model: odd days at midnight UTC
- Startup job enqueueing

### test_broker.py
Tests for Dramatiq broker:
- Broker configuration
- Actor registration
- Actor naming
- Retry options configuration

## Test Fixtures (conftest.py)

### Environment
- `jobs_env`: Sets up required environment variables

### Mock Data
- `sample_systems`: Mock system objects from API
- `sample_datastreams`: Mock datastream objects
- `sample_weather_current`: Open Meteo current weather response
- `sample_weather_hourly`: Open Meteo hourly weather response
- `mock_httpx_client`: Mocked HTTP client with pre-configured responses

## Key Testing Features

### Mocking Strategy
- Uses `unittest.mock` for all external dependencies
- HTTP calls are mocked with realistic Open Meteo API responses
- Redis/database calls are mocked
- Prophet model training is mocked

### Historical Data Testing
Tests specifically verify the retry behavior for historical data:
- When a job retries, it fetches hourly data instead of current data
- Result time is preserved across retries
- Correct hour is extracted from hourly response

### Error Scenarios
- API not found errors
- Missing datastreams
- Missing weather data fields
- HTTP errors

## Running from Docker

When running tests in the Docker container:

```bash
docker compose exec jobs-worker pytest
docker compose exec jobs-worker pytest tests/test_tasks.py -v
```

Or build and run a test-focused image:

```bash
docker compose exec jobs-worker poetry run pytest
```

## Notes

- Tests use synchronous mocking of Dramatiq actors (no actual queue needed)
- All external API calls are mocked
- Tests verify both happy path and error scenarios
- Cron job triggers are validated via `CronTrigger` mock verification
