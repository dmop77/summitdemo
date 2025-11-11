# Quick Test Guide - Pulpoo Voice Assistant

## ⚡ Quick Start (2 minutes)

### 1. Navigate to Project
```bash
cd ~/Desktop/Sim-Tech/summit\ demo/summitdemo
source venv/bin/activate
```

### 2. Run All Tests
```bash
cd agent
pytest tests/ -v
```

**Expected Result**: 22 passed in ~3.90 seconds ✓

## 📋 Common Test Commands

### Run Specific Tests
```bash
# Pulpoo tests only
pytest tests/test_pulpoo.py -v

# Web scraper tests only
pytest tests/test_web_scraper.py -v

# Single test class
pytest tests/test_pulpoo.py::TestPulpooConnection -v

# Single test
pytest tests/test_pulpoo.py::TestPulpooConnection::test_create_appointment_with_mock -v
```

### Run with Filters
```bash
# Unit tests only (no integration)
pytest tests/ -m "not integration" -v

# Integration tests only (requires API keys)
pytest tests/ -m integration -v

# Tests matching pattern
pytest tests/ -k "appointment" -v
```

### Run with Coverage
```bash
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html  # View coverage report
```

## 🔍 Test Files at a Glance

### test_pulpoo.py (13 tests)
- **Configuration tests**: API key and URL validation
- **Appointment tests**: Creation, payload, error handling
- **Integration test**: Real API call (requires PULPOO_API_KEY)
- **Error tests**: Timeout, connection, invalid responses

### test_web_scraper.py (9 tests)
- **Scraper tests**: HTML parsing, content extraction
- **AI tests**: Summarization, embedding generation
- **Error tests**: Network failures, size limits
- **Integration test**: Real website scraping

## 🚀 Running the Server

### Start Server
```bash
cd ~/Desktop/Sim-Tech/summit\ demo/summitdemo
source venv/bin/activate
python agent/main.py
```

**Expected Output**:
```
Starting Voice Agent Server
Using: Deepgram STT + OpenAI LLM + OpenAI TTS + Web Scraping
Server running on http://0.0.0.0:8084
```

### Test Server is Running
```bash
# In another terminal
curl http://localhost:8084/
```

## 🛠️ Troubleshooting

### Tests Won't Run
```bash
# Make sure you're in agent directory
cd agent

# Check pytest is installed
python -m pytest --version

# Install/update test dependencies
pip install pytest pytest-asyncio pytest-cov
```

### Import Errors
```bash
# Make sure venv is activated
source ../venv/bin/activate

# Reinstall requirements
pip install -r ../agent/requirements.txt
```

### Server Won't Start
```bash
# Check Python version (need 3.9+)
python --version

# Check for port conflicts
lsof -i :8084  # macOS/Linux
netstat -ano | findstr :8084  # Windows
```

## 📊 Test Coverage Summary

| Component | Tests | Status |
|-----------|-------|--------|
| Pulpoo API | 13 | ✓ All Pass |
| Web Scraper | 9 | ✓ All Pass |
| **Total** | **22** | **✓ 100%** |

## 🎯 What Gets Tested

### Pulpoo API
- ✓ Configuration validation
- ✓ Appointment creation
- ✓ Request structure
- ✓ Error handling
- ✓ Available slots
- ✓ DateTime formatting
- ✓ Duration handling
- ✓ Network timeouts
- ✓ Connection failures

### Web Scraper
- ✓ Module initialization
- ✓ HTML parsing
- ✓ Content extraction
- ✓ Content summarization
- ✓ Embedding generation
- ✓ Combined operations
- ✓ Error handling
- ✓ Size limiting
- ✓ Real website scraping

## 🔑 Environment Variables (Optional for Integration Tests)

```bash
# Required for integration tests only
export OPENAI_API_KEY="sk-..."
export DEEPGRAM_API_KEY="..."
export PULPOO_API_KEY="..."
```

## 📝 Test Output Interpretation

### Passing Test
```
test_pulpoo.py::TestPulpooConnection::test_create_appointment_with_mock PASSED [23%]
```

### Skipped Test (OK)
```
test_pulpoo.py::TestPulpooIntegration::test_real_appointment_creation SKIPPED (no PULPOO_API_KEY)
```

### Failed Test
```
test_pulpoo.py::TestPulpooConnection::test_something FAILED [50%]
AssertionError: assert True == False
```

## 🚦 Test Status Indicators

| Symbol | Meaning |
|--------|---------|
| ✓ PASSED | Test succeeded |
| ✗ FAILED | Test failed (shows error) |
| S SKIPPED | Test skipped (usually missing API key) |
| E ERROR | Test had an error (not assertion failure) |

## 💡 Pro Tips

1. **Run one test at a time while debugging**
   ```bash
   pytest tests/test_pulpoo.py::TestPulpooConnection::test_create_appointment_with_mock -v -s
   ```

2. **Show print statements**
   ```bash
   pytest tests/ -v -s
   ```

3. **Stop on first failure**
   ```bash
   pytest tests/ -x
   ```

4. **Run only last failed test**
   ```bash
   pytest tests/ --lf -v
   ```

5. **Run tests in random order**
   ```bash
   pytest tests/ --random-order-bucket=global
   ```

## 🎓 Understanding Test Structure

```python
# Test file organization
tests/
├── conftest.py          # Shared fixtures for all tests
├── test_pulpoo.py       # Pulpoo API tests
└── test_web_scraper.py  # Web scraper tests

# Test class naming
class Test<Feature>:
    def test_<scenario>(self):
        # Arrange: Set up test data
        # Act: Execute the code being tested
        # Assert: Verify the results
```

## 📞 Need Help?

1. **Check TESTING_GUIDE.md** - Comprehensive testing documentation
2. **Check TESTING_SUMMARY.md** - Detailed test results
3. **Check SESSION_REPORT.md** - Bug fixes and history
4. **Read test files directly** - Comments explain each test

---

**Quick Command Reference**:
```bash
# Install and run tests
cd agent && pytest tests/ -v

# Just Pulpoo tests
pytest tests/test_pulpoo.py -v

# With coverage
pytest tests/ --cov=. --cov-report=html

# Start the server
python agent/main.py
```

Happy testing! 🎉
