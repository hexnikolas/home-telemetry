# Notifier Service Tests

Comprehensive test suite for the Notifier microservice, including alert rule evaluation, Redis health monitoring, Docker container monitoring, and API integration.

## Test Coverage

### test_main.py
- **TestEvaluateCondition**: Tests alert condition evaluation (>, <, >=, <=, =)
- **TestNotifierServiceInit**: Initialization and default state
- **TestNotifierServiceAlert**: Alert sending to Gotify
- **TestNotifierServiceCooldown**: Alert cooldown/deduplication logic
- **TestNotifierServiceRedisHealth**: Redis connection health monitoring
- **TestNotifierServiceAPIToken**: OAuth2 token management and caching
- **TestNotifierServiceRedisGrace**: Redis grace period during recovery

### test_rules.py
- **TestRulesLoading**: YAML rules file loading and error handling
- **TestRuleStructure**: Rule definition validation

## Installation

Install test dependencies:

```bash
cd services/notifier
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
pytest tests/test_main.py
```

### Run specific test class
```bash
pytest tests/test_main.py::TestEvaluateCondition
```

### Run with coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run async tests only
```bash
pytest tests/ -k "async"
```

## Test Fixtures

Fixtures defined in `conftest.py`:

- `mock_redis`: Mock async Redis client with all required methods
- `mock_docker_client`: Mock Docker client
- `sample_rules`: Sample alert rules for testing
- `mock_rules_file`: Temporary YAML rules file
- `notifier_env`: Environment variable setup
- `event_loop`: Async event loop for tests

## Key Testing Patterns

### Mocking Redis
```python
async def test_example(self, mock_redis):
    service = NotifierService()
    mock_redis.get = AsyncMock(return_value="value")
    service.redis = mock_redis
    # Test code
```

### Testing Async Functions
```python
@pytest.mark.asyncio
async def test_async_function(self):
    # Test code using await
```

### Patching Environment Variables
```python
def test_with_env(self, monkeypatch):
    monkeypatch.setenv("GOTIFY_URL", "http://test")
    # Test code
```

## Notes

- Tests use `pytest-asyncio` for async test support
- All Redis calls are mocked to avoid requiring a running Redis instance
- Docker client is mocked for container health tests
- HTTP calls are mocked using `unittest.mock.patch`
