# Quick Start Guide

Get the Voice Agent running in 5 minutes.

## Step 1: Setup (2 minutes)

```bash
cd agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 2: Configure (1 minute)

Create `.env` file with your API keys:

```bash
# Copy example
cp .env.example .env

# Edit with your actual keys
nano .env  # or your favorite editor
```

Required keys:
- `OPENAI_API_KEY` - Get from https://platform.openai.com/api-keys
- `DEEPGRAM_API_KEY` - Get from https://console.deepgram.com
- `PULPOO_API_KEY` - Get from your Pulpoo account

## Step 3: Run (1 minute)

```bash
python main.py
```

Wait for:
```
✓ Server listening on http://0.0.0.0:8084
✓ Open http://localhost:8084 in your browser
```

## Step 4: Test (1 minute)

1. Open browser: `http://localhost:8084`
2. Click "Start"
3. Enter your name, email, and website
4. Talk to the agent
5. Watch appointment get created in Pulpoo

## Testing the Agent

### Run Unit Tests
```bash
pytest tests/test_agent.py -v
```

Expected output:
```
test_agent.py::test_appointment_scheduler_initialization PASSED
test_agent.py::test_appointment_scheduler_missing_api_key PASSED
test_agent.py::test_appointment_scheduler_invalid_date PASSED
test_agent.py::test_appointment_scheduler_successful_creation PASSED
======================== 4 passed in 0.08s =========================
```

### Manual Testing

1. **Setup Phase**
   - Enter name, email, website
   - See agent acknowledge your business

2. **Conversation Phase**
   - Chat naturally about your needs
   - Agent understands context from website

3. **Scheduling Phase**
   - Agent suggests scheduling
   - Provide preferred time
   - Watch appointment appear in Pulpoo

## Common Issues

### Port Already in Use
```bash
# Use different port
PORT=8085 python main.py
```

### API Key Errors
```
Error: OpenAI API key not configured
Solution: Check .env file has OPENAI_API_KEY=sk-...
```

### No Audio Input
```
Error: Deepgram connection failed
Solution: Check DEEPGRAM_API_KEY and internet connection
```

### Appointment Not Created
```
Check logs for: "Error in schedule_appointment"
Verify PULPOO_API_KEY is correct
```

## File Structure

```
agent/
├── main.py              ← Start here (python main.py)
├── voice_agent.py       ← Conversation logic
├── agent_tools.py       ← Pulpoo scheduling
├── config.py            ← Configuration
├── requirements.txt     ← Dependencies
├── .env                 ← Your API keys (create this)
├── .env.example         ← Template
├── README.md            ← Full documentation
└── tests/               ← Unit tests
```

## Next Steps

1. ✅ Run `python main.py`
2. ✅ Test in browser
3. ✅ Check Pulpoo for created appointments
4. ✅ Run tests: `pytest tests/test_agent.py -v`
5. ✅ Review README.md for full documentation

## Tips

- **First time slow?** OpenAI model might be downloading. This is normal.
- **Want to see logs?** Run with `DEBUG=true python main.py`
- **Having issues?** Check the logs in console output
- **Want to customize?** Edit system prompt in `voice_agent.py`

## Example Conversation

```
System: "Hello! I'm here to help you schedule an appointment."
You: "Hi, I'm interested in discussing a project"
Agent: "Great! I can see you work in [industry]. 
        What would be a good time for you to meet?"
You: "How about next Tuesday at 2 PM?"
Agent: "Perfect! I'm scheduling your appointment for 
        Tuesday at 2:00 PM. This will be added to Pulpoo."
[Appointment created in Pulpoo]
```

---

**That's it! You're ready to go.** 🚀
