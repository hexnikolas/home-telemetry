# Jobs Service Tests

Comprehensive test suite for the Jobs microservice, including handler functions, scheduler configuration, and API integration.

## Test Coverage

### test_handlers.py
- **TestTokenManager**: OAuth2 token fetching, caching, and refresh logic
- **TestSyncMqttTopicsHandler**: MQTT topic synchronization from API to Redis
- **TestFetchOpenMeteoHandler**: Open Meteo weather data API integration
- **TestProcessObservationsHandler**: Observation data processing

### test_scheduler.py
- **TestRedisSettings**: Redis connection settings parsing
- **TestSchedulerConfig**: Cron job configuration validation
- **TestPublishSchedules**: Publishing schedules to Redis
- **TestWorkerSettings**: ARQ worker configuration

## Installation

Install test dependencies:

```bash
cd services/jobs
pip install -e ".[test]"
```

Or with Poetry:

```bash
poetry install --with test
```

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run specific test file
```bash
pytest tests/test_handlers.py
```

### Run specific test class
```bash
pytest tests/test_handlers.py::TestTokenManager
```

### Run with coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run only synchronous tests
```bash
pytest tests/ -k "not async"
```

## Test Fixtures

Fixtures defined in `conftest.py`:

- `mock_redis`: Mock async Redis client
- `jobs_env`: Environment variable setup
- `mock_api_context`: ARQ job context mock
- `sample_systems`: Sample system data from API
- `sample_datastreams`: Sample datastream data from API
- `sample_weather_data`: Sample Open Meteo API response
- `mock_httpx_client`: Mock httpx async client
- `mock_token_manager`: Mock OAuth2 token manager
- `event_loop`: Async event loop for tests

## Key Testing Patterns

### Testing Handler Functions
```python
@pytest.mark.asyncio
async def test_handler(self, mock_api_context):
    result = await handle_sync_mqtt_topics_to_redis(mock_api_context)
    # Assert on result
```

### Mocking API Responses
```python
with patch("app.handlers.httpx.AsyncClient") as mock_client_class:
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"data": "value"})
    mock_client.get = AsyncMock(return_value=mock_response)
    # Use in test
```

### Testing Token Caching
```python
@pytest.mark.asyncio
async def test_token_caching(self):
    manager = TokenManager()
    manager._token = "cached-token"
    manager._expires_at = 9999999999  # Future
    token = await manager.get_token()
    assert token == "cached-token"
```

## Notes

- Tests use `pytest-asyncio` for async test support
- All Redis calls are mocked to avoid requiring running services
- HTTP calls are mocked to avoid external API calls during testing
- ARQ jobs run within test context and don't actually execute in background
