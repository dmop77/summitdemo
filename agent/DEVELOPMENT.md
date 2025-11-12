# Development Guide

Guide for developers working on the Voice Agent.

## Architecture Overview

The system uses a **conversation-driven approach**:

```
┌─────────────┐
│   Client    │ (Browser with voice input/output)
└──────┬──────┘
       │
       └── WebSocket ──→ main.py (aiohttp server)
                            ├── VoiceServer (handles connections)
                            └── BackgroundAgent (conversation logic)
                                    └── AppointmentScheduler
                                            └── Pulpoo API
```

## Core Files

### `main.py` - Server
- Handles HTTP setup endpoint
- Manages WebSocket connections
- Coordinates voice input/output
- Creates VoiceServer instance

**Key Classes:**
- `VoiceServer` - Main server that handles requests
- Handles both setup (name/email/website) and WebSocket (voice)

### `voice_agent.py` - Conversation Manager
- Manages conversation state and context
- Uses Pydantic AI for intelligent responses
- Decides when to schedule appointments
- Tracks user information and conversation history

**Key Class:**
- `BackgroundAgent` - The LLM-powered agent
  - `process_message()` - Handle user input
  - `set_user_info()` - Initialize with user context
  - `_schedule_appointment_tool()` - Pulpoo integration

### `agent_tools.py` - Scheduling
- Single responsibility: Create appointments in Pulpoo
- Handles API calls and error handling
- Formats appointment data

**Key Class:**
- `AppointmentScheduler` - Pulpoo API wrapper
  - `schedule_appointment()` - Create appointment

### `config.py` - Configuration
- Loads environment variables
- Provides config objects
- Type-safe settings with Pydantic

**Key Functions:**
- `get_voice_config()` - Get voice provider settings
- `get_agent_config()` - Get agent behavior settings

### `web_scraper.py` - Web Content
- Scrapes websites
- Extracts business information
- Generates embeddings

### `schemas.py` - Data Models
- Pydantic models for type safety
- Conversation context
- User information
- API responses

## Development Workflow

### Adding a New Feature

1. **Plan**: Define what the agent should do
2. **Update System Prompt**: Modify prompt in `BackgroundAgent._build_system_prompt()`
3. **Add Tool if Needed**: Create method and decorate with `@agent.tool`
4. **Test**: Write tests in `tests/test_agent.py`
5. **Document**: Update README or DEVELOPMENT.md

### Example: Adding a New Tool

```python
# In voice_agent.py, add to BackgroundAgent class

async def _send_email_tool(self, ctx: RunContext, recipient: str, subject: str, body: str) -> str:
    """Tool for sending emails."""
    try:
        # Implementation
        return "Email sent successfully"
    except Exception as e:
        return f"Failed to send email: {e}"
```

Then register it in `__init__`:
```python
self.agent = Agent(
    model=model,
    tools=[self._schedule_appointment_tool, self._send_email_tool],  # Add here
    system_prompt=self._build_system_prompt(),
)
```

## Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test
```bash
pytest tests/test_agent.py::test_appointment_scheduler_initialization -v
```

### Run with Coverage
```bash
pytest --cov=. tests/
```

### Add a Test

```python
# In tests/test_agent.py

@pytest.mark.asyncio
async def test_my_new_feature():
    """Test description."""
    scheduler = AppointmentScheduler(
        openai_api_key="test",
        pulpoo_api_key="test"
    )
    # Your test code
    assert result["success"] is True
```

## Common Modifications

### Change Agent Behavior

Edit `voice_agent.py`, method `_build_system_prompt()`:

```python
def _build_system_prompt(self) -> str:
    prompt = """You are a friendly appointment scheduling assistant.
    
    [Customize behavior here]
    """
    return prompt
```

### Add New Pulpoo Fields

Edit `agent_tools.py`, in `schedule_appointment()`:

```python
payload = {
    "title": f"Appointment: {appointment_topic}",
    "description": description,
    "assigned_to_email": "perezmd324@gmail.com",
    "deadline": deadline,
    "importance": "HIGH",
    # Add new field here:
    "custom_field": "value",
}
```

### Change Server Port

Use environment variable:
```bash
PORT=9000 python main.py
```

Or edit `.env`:
```
PORT=9000
```

## Debugging

### Enable Debug Logging

```bash
DEBUG=true python main.py
```

### Print Debug Info

```python
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Debug info: {variable}")
```

### Check Imports

```bash
python -c "from agent_tools import AppointmentScheduler; print('OK')"
```

### Mock External APIs

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_with_mock():
    with patch('aiohttp.ClientSession') as mock:
        # Setup mock
        mock.post.return_value = AsyncMock(status=201)
        # Run test
```

## Performance Considerations

### Token Usage
- Keep prompts concise
- Avoid storing full conversation in context
- Use summaries instead of transcripts

### API Calls
- Cache website scraping results
- Batch appointments if possible
- Use connection pooling

### Memory
- Clear old conversations regularly
- Don't store large arrays in memory
- Use streaming for long responses

## Code Style

### Format Code
```bash
black *.py
```

### Lint Code
```bash
ruff check *.py
```

### Type Hints
Always use type hints:
```python
async def process_message(self, user_input: str, session_id: str) -> str:
    """Process user message."""
    pass
```

## Dependencies

### Adding a New Dependency

1. Install it:
```bash
pip install new-package
```

2. Add to requirements.txt:
```
new-package>=version
```

3. Test imports:
```bash
python -c "import new_package; print('OK')"
```

4. Run tests to ensure nothing broke

## Deployment

### Local Testing
```bash
python main.py
```

### Production Considerations
- Use environment variables for all secrets
- Enable error logging
- Set `DEBUG=false`
- Use proper error handling
- Monitor API quotas

### Environment Variables for Production
```env
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
PULPOO_API_KEY=...
DEBUG=false
PORT=8084
```

## Contributing

1. Create a branch for your feature
2. Make changes with tests
3. Run tests: `pytest tests/ -v`
4. Format code: `black *.py`
5. Commit with clear message
6. Submit for review

## Useful Commands

```bash
# Run tests
pytest tests/ -v

# Format code
black *.py

# Check imports
python -c "from voice_agent import BackgroundAgent; print('OK')"

# Start server
python main.py

# Install dependencies
pip install -r requirements.txt

# Create virtual env
python -m venv venv
source venv/bin/activate
```

## Resources

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [aiohttp Documentation](https://docs.aiohttp.org/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)

---

Happy developing! 🚀
