# Voice Agent - Appointment Scheduling System

A real-time voice AI agent that schedules appointments by scraping user websites, understanding their business context, and creating appointments in Pulpoo.

## 🎯 How It Works

### Conversation Flow
1. **Setup Phase**: User provides name, email, and website URL
2. **Web Scraping**: Agent scrapes and understands the user's website
3. **Greeting**: Agent greets user by name and acknowledges their business
4. **Natural Chat**: Brief conversation about their needs
5. **Scheduling**: Agent suggests appointment and collects preferred time
6. **Pulpoo Creation**: Creates appointment task in Pulpoo with full context

### Tech Stack
- **Voice**: Deepgram STT + OpenAI TTS (via aiohttp WebSocket)
- **AI Agent**: Pydantic AI with OpenAI LLM
- **Scheduling**: Direct Pulpoo API integration
- **Server**: aiohttp with WebSocket support
- **Database**: Conversation context tracking

## 📋 Prerequisites

- Python 3.9+
- API Keys:
  - OpenAI (for LLM and TTS)
  - Deepgram (for STT)
  - Pulpoo (for appointment creation)

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the agent directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Deepgram Configuration
DEEPGRAM_API_KEY=...
DEEPGRAM_MODEL=nova-3

# Pulpoo Configuration
PULPOO_API_KEY=...
PULPOO_API_URL=https://api.pulpoo.com/v1/external/tasks/create

# Server Configuration
HOST=0.0.0.0
PORT=8084
DEBUG=false
```

### 3. Run the Server

```bash
python main.py
```

You should see:
```
✓ Server listening on http://0.0.0.0:8084
✓ Open http://localhost:8084 in your browser
Ready to accept connections!
```

### 4. Access the Interface

Open your browser to `http://localhost:8084`

## 📦 Project Structure

```
agent/
├── main.py                 # Server entry point (aiohttp)
├── voice_agent.py         # BackgroundAgent - context-aware conversation manager
├── agent_tools.py         # AppointmentScheduler - Pulpoo API integration
├── web_scraper.py         # Website scraping and embedding
├── config.py              # Configuration management
├── schemas.py             # Pydantic data models
├── tests/
│   └── test_agent.py      # Unit tests for appointment scheduling
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## 🔧 Core Components

### BackgroundAgent (`voice_agent.py`)
The main conversation manager that:
- Maintains conversation context (user info, conversation state)
- Manages conversation flow with state tracking
- Uses Pydantic AI to generate intelligent responses
- Calls appointment scheduling tool when appropriate

**Key Methods:**
- `process_message()` - Handle user input and generate agent response
- `set_user_info()` - Set user context from setup phase
- `reset()` - Reset for new conversation

### AppointmentScheduler (`agent_tools.py`)
Handles appointment creation with:
- Pulpoo API integration
- User information and conversation summary
- Error handling and validation

**Key Method:**
- `schedule_appointment()` - Create appointment in Pulpoo

### System Flow

```
User Message
    ↓
Voice Input (Deepgram STT)
    ↓
BackgroundAgent.process_message()
    ↓
LLM (OpenAI GPT-4o-mini)
    ↓
[Check if scheduling needed]
    ├─ Yes → AppointmentScheduler.schedule_appointment()
    │           ↓
    │        Pulpoo API
    │
    └─ No → Continue conversation
    ↓
Voice Output (OpenAI TTS)
    ↓
User Hears Response
```

## 🧪 Testing

Run the test suite:

```bash
pytest tests/test_agent.py -v
```

Tests cover:
- Appointment scheduler initialization
- API key validation
- Date format validation
- Successful appointment creation with mocked Pulpoo API

## 📝 API Endpoints

### WebSocket
- **Path**: `/ws`
- **Protocol**: WebSocket for real-time audio streaming
- **Purpose**: Handle voice input/output in real-time

### HTTP Setup
- **Path**: `/api/setup`
- **Method**: POST
- **Body**: `{"name": "...", "email": "...", "website_url": "..."}`
- **Purpose**: Initialize user context and scrape website

## 🔐 Security Notes

- API keys are loaded from `.env` (never commit to git)
- `.gitignore` excludes sensitive files
- Pulpoo API calls use secure headers
- WebSocket connections are session-based

## 📊 Conversation Context

The agent maintains:
- **User Info**: Name, email, website URL
- **Conversation History**: All user and agent messages
- **State**: Current phase (greeting, conversation, scheduling, etc.)
- **Website Summary**: Scraped business information

## 🐛 Troubleshooting

### "OpenAI API key not configured"
- Check `.env` file has `OPENAI_API_KEY`
- Ensure key is valid and has proper permissions

### "Connection to Deepgram failed"
- Verify `DEEPGRAM_API_KEY` is correct
- Check internet connection
- Ensure Deepgram service is up

### "Appointment creation failed"
- Verify `PULPOO_API_KEY` is correct
- Check Pulpoo API endpoint is accessible
- Review error message in logs for details

### WebSocket connection issues
- Ensure firewall allows port 8084
- Check browser console for errors
- Verify server is running (`python main.py`)

## 📚 Dependencies

Main packages:
- `pydantic-ai` - AI agent framework
- `openai` - OpenAI API client
- `aiohttp` - Async HTTP client/server
- `pydantic` - Data validation
- `python-dotenv` - Environment variable management

See `requirements.txt` for full list.

## 🎓 How the Agent Decides to Schedule

The agent uses the system prompt to understand when to call the scheduling tool:
1. It tracks conversation state
2. When user indicates interest in scheduling
3. After collecting necessary time information
4. It automatically calls `schedule_appointment_tool`
5. The LLM passes context about the appointment

The tool integration is automatic - the LLM learns to use tools through its system prompt and the function signature.

## 🚀 Performance

- **Latency**: Real-time with sub-second response times
- **Concurrency**: Handles multiple concurrent conversations
- **Reliability**: Error handling for API failures with fallbacks
- **Efficiency**: Minimal token usage with focused prompts

## 📞 Support

For issues or questions:
1. Check logs in console output
2. Review `.env` configuration
3. Verify all API keys are valid
4. Check network connectivity
5. Run tests: `pytest tests/test_agent.py -v`

## 📄 License

See LICENSE file in repository root.
