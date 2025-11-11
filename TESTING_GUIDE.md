# Pulpoo Voice Assistant - Testing Guide

Complete guide for testing the Pulpoo Voice Assistant, including Pulpoo API connection tests.

## 📋 Test Structure

```
agent/tests/
├── __init__.py           # Test package initialization
├── conftest.py           # Shared fixtures and configuration
├── pytest.ini            # Pytest configuration
├── test_pulpoo.py        # Pulpoo API connection tests
├── test_web_scraper.py   # Web scraping functionality tests
└── test_agent_tools.py   # Agent tools tests (coming soon)
```

## 🚀 Quick Start Testing

### 1. Install Test Dependencies

```bash
cd summitdemo
source venv/bin/activate
pip install pytest pytest-asyncio pytest-cov
```

### 2. Run All Tests

```bash
cd agent
pytest
```

### 3. Run Specific Test Categories

```bash
# Only Pulpoo tests
pytest tests/test_pulpoo.py -v

# Only web scraper tests
pytest tests/test_web_scraper.py -v

# Only integration tests (requires real API keys)
pytest -m integration

# Skip integration tests
pytest -m "not integration"
```

## 🧪 Test Categories

### Unit Tests (No External Dependencies)

Tests that use mocked HTTP responses and don't require real API calls.

```bash
# Run unit tests only
pytest -m "not integration" -v
```

**Coverage:**
- Appointment creation payload validation
- Error handling and recovery
- DateTime formatting
- Duration settings
- Mock API responses

### Integration Tests (Requires API Keys)

Tests that make real API calls to Deepgram, OpenAI, and Pulpoo.

```bash
# Run integration tests only
pytest -m integration -v
```

**Warning:** Integration tests will:
- Use real API calls (and consume credits)
- Require valid API keys in `.env`
- Take longer to run
- Make real HTTP requests

## 📝 Pulpoo Connection Tests

### Test File: `test_pulpoo.py`

Comprehensive tests for Pulpoo API integration.

#### Test Classes

1. **TestPulpooConnection**
   - Configuration validation
   - Appointment creation
   - Error handling
   - API payload verification

2. **TestPulpooIntegration**
   - Real API connection tests
   - Actual appointment creation
   - End-to-end workflow

3. **TestPulpooErrorScenarios**
   - Timeout handling
   - Connection errors
   - Invalid responses
   - Server errors

### Running Pulpoo Tests

```bash
# All Pulpoo tests
pytest tests/test_pulpoo.py -v

# Specific test
pytest tests/test_pulpoo.py::TestPulpooConnection::test_create_appointment_with_mock -v

# With output
pytest tests/test_pulpoo.py -v -s
```

### Test Descriptions

#### 1. Configuration Tests

```python
# Test that Pulpoo API key is configured
test_pulpoo_api_key_configured()

# Test that API URL is valid
test_pulpoo_api_url_valid()
```

**What it checks:**
- API key is not empty
- API URL contains "pulpoo"
- URL uses HTTP/HTTPS

#### 2. Appointment Creation Tests

```python
# Test with mocked response
test_create_appointment_with_mock()

# Test payload structure
test_appointment_creation_payload()

# Test error handling
test_appointment_creation_error_handling()
```

**What it checks:**
- Correct POST request to Pulpoo
- Proper authorization headers
- Valid JSON payload
- Correct error responses

#### 3. Integration Tests

```python
# Real appointment creation with valid credentials
test_real_appointment_creation()
```

**What it checks:**
- Actual Pulpoo API connectivity
- Real appointment creation
- Response parsing
- Appointment confirmation

#### 4. Error Handling Tests

```python
# Timeout handling
test_pulpoo_timeout()

# Connection errors
test_pulpoo_connection_error()

# Invalid responses
test_pulpoo_invalid_response()
```

**What it checks:**
- Graceful error recovery
- User-friendly error messages
- No crashes on failures

## 📊 Web Scraper Tests

### Test File: `test_web_scraper.py`

Tests for website scraping and content extraction.

```bash
# All web scraper tests
pytest tests/test_web_scraper.py -v

# Only unit tests
pytest tests/test_web_scraper.py -m "not integration" -v
```

### Test Coverage

- HTML parsing
- Content extraction
- Summary generation
- Embedding creation
- Error handling
- Content size limits

## 🔧 Test Fixtures

Shared test data defined in `conftest.py`:

```python
@pytest.fixture
def sample_appointment_data():
    """Sample appointment for testing."""
    return {
        "user_name": "John Doe",
        "user_email": "john@example.com",
        "topic": "Website Discussion",
    }

@pytest.fixture
def sample_html_content():
    """Sample HTML for scraping tests."""
    return "<html>...</html>"

@pytest.fixture
def mock_config():
    """Mock configuration object."""
    # Pre-configured with test values
```

### Using Fixtures

```python
def test_something(sample_appointment_data, mock_config):
    """Test using fixtures."""
    # Use the fixture data
    assert sample_appointment_data["user_name"] == "John Doe"
```

## 🎯 Running Specific Tests

### By Test Class

```bash
# Run all tests in TestPulpooConnection
pytest tests/test_pulpoo.py::TestPulpooConnection -v
```

### By Test Method

```bash
# Run specific test
pytest tests/test_pulpoo.py::TestPulpooConnection::test_create_appointment_with_mock -v
```

### By Pattern

```bash
# Run all tests matching pattern
pytest -k "appointment" -v
```

### By Marker

```bash
# Run only integration tests
pytest -m integration -v

# Run only unit tests
pytest -m "not integration" -v
```

## 📈 Test Execution Examples

### Example 1: Quick Unit Test Run

```bash
cd agent
pytest tests/test_pulpoo.py::TestPulpooConnection::test_create_appointment_with_mock -v -s
```

Expected output:
```
test_pulpoo.py::TestPulpooConnection::test_create_appointment_with_mock PASSED
✓ Mock appointment created: {'success': True, ...}
```

### Example 2: Full Test Suite

```bash
cd agent
pytest tests/ -v --tb=short
```

Expected output:
```
test_pulpoo.py::TestPulpooConnection::test_pulpoo_api_key_configured PASSED
test_pulpoo.py::TestPulpooConnection::test_pulpoo_api_url_valid PASSED
test_pulpoo.py::TestPulpooConnection::test_create_appointment_with_mock PASSED
...
```

### Example 3: Integration Testing

```bash
cd agent
pytest -m integration -v -s
```

Expected output:
```
✓ Real Pulpoo Integration Test Result:
  Success: True
  Appointment ID: apt_12345
  Scheduled: 2025-11-12T10:00:00
  Message: Appointment scheduled for November 12 at 10:00 AM
```

## 🔍 Troubleshooting Tests

### Issue: Tests Cannot Find Modules

**Solution:**
```bash
# Make sure you're in the agent directory
cd agent

# Or add agent directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Issue: AsyncIO Tests Failing

**Solution:**
```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Make sure pytest.ini has asyncio_mode = auto
```

### Issue: OpenAI API Tests Failing

**Solution:**
- Verify `OPENAI_API_KEY` is set in `.env`
- Check that you have credits on your OpenAI account
- Test with integration marker: `pytest -m integration`

### Issue: Pulpoo Tests Skipped

**Solution:**
- Verify `PULPOO_API_KEY` is set in `.env`
- Check that API key is not empty
- Run with verbose flag to see skip reasons: `pytest -v`

## 📊 Test Coverage

To measure code coverage:

```bash
# Install coverage
pip install pytest-cov

# Run tests with coverage report
pytest --cov=. --cov-report=html

# View report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
# or
start htmlcov/index.html  # Windows
```

## ✅ Test Validation Checklist

Before deploying, ensure all tests pass:

- [ ] All unit tests pass (`pytest -m "not integration"`)
- [ ] Pulpoo connection tests pass
- [ ] Web scraper tests pass
- [ ] Agent tools tests pass
- [ ] Integration tests pass (with valid API keys)
- [ ] No deprecation warnings
- [ ] Code coverage > 80%

## 🚀 Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r agent/requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Run tests
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        DEEPGRAM_API_KEY: ${{ secrets.DEEPGRAM_API_KEY }}
        PULPOO_API_KEY: ${{ secrets.PULPOO_API_KEY }}
      run: |
        cd agent
        pytest tests/ -m "not integration" -v
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

## 🤝 Writing New Tests

### Test Template

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestMyFeature:
    """Test description."""
    
    @pytest.fixture
    def my_fixture(self):
        """Fixture description."""
        return {"data": "value"}
    
    @pytest.mark.asyncio
    async def test_something(self, my_fixture):
        """Test description."""
        # Setup
        expected = "result"
        
        # Execute
        result = await some_function()
        
        # Verify
        assert result == expected
        print(f"✓ Test passed: {result}")
```

### Best Practices

1. **Name tests clearly**: `test_appointment_creation_with_valid_data`
2. **Use descriptive assertions**: Include messages
3. **Mock external calls**: Don't make real API calls in unit tests
4. **Organize by feature**: Group related tests in classes
5. **Use fixtures**: Share common setup code
6. **Test error cases**: Not just happy paths
7. **Add print statements**: For debugging with `-s` flag

---

Happy testing! 🧪

For questions, see `README.md` or `QUICK_START.md`.
