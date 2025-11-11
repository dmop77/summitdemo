# Voice Agent - Pydantic AI

A production-ready voice AI agent built with Pydantic AI, Deepgram (STT), and OpenAI (LLM).

## Features

- **Pydantic AI Framework**: Type-safe AI agent with structured outputs
- **Deepgram STT**: High-quality speech-to-text transcription
- **OpenAI LLM**: GPT-4o-mini for intelligent responses
- **Optional TTS**: OpenAI or Cartesia text-to-speech
- **Real-time WebSocket**: Live audio streaming and responses
- **Task Creation**: Integration with Pulpoo API for task management

## Architecture

```
agent/
├── main.py              # WebSocket server & HTTP endpoints
├── voice_agent.py       # Pydantic AI agent logic
├── config.py            # Configuration management (Pydantic)
├── schemas.py           # Data models (Pydantic)
└── requirements.txt     # Dependencies
```

## Setup

### 1. Install Dependencies

```bash
cd agent
python -m pip install -r requirements.txt
```

### 2. Environment Configuration

Create `.env` file in the agent directory:

```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Deepgram (Speech-to-Text)
DEEPGRAM_API_KEY=...
DEEPGRAM_MODEL=nova-3

# Text-to-Speech (choose one)
# OpenAI TTS (default)
OPENAI_TTS_VOICE=echo

# OR Cartesia TTS (optional)
# CARTESIA_API_KEY=...
# CARTESIA_VOICE_ID=...

# Pulpoo API (task creation - optional)
PULPOO_API_KEY=...

# Server
PORT=8084
HOST=0.0.0.0
DEBUG=false
```

### 3. Run the Agent

```bash
python main.py
```

Visit `http://localhost:8084` in your browser to test.

## File Descriptions

### `main.py`
- WebSocket server using aiohttp
- Handles audio streaming and real-time communication
- Integrates Deepgram for speech transcription
- Integrates OpenAI for TTS

### `voice_agent.py`
- Pydantic AI agent implementation
- Handles conversation logic
- Manages Pulpoo task creation
- Maintains conversation context

### `config.py`
- Pydantic Settings for environment configuration
- Supports multiple STT providers (Deepgram, OpenAI)
- Supports multiple TTS providers (OpenAI, Cartesia)
- Type-safe configuration with validation

### `schemas.py`
- Pydantic models for data validation
- User info, conversation context, appointments
- Scraped content and web scraper requests
- Modern Pydantic v2 syntax with ConfigDict

## Configuration Options

### Speech-to-Text Providers

**Deepgram (Recommended)**
- Model: `nova-3` (latest) or `nova-2`
- Fast and accurate transcription

**OpenAI (Fallback)**
- Uses Whisper API
- Good for fallback scenarios

### Text-to-Speech Providers

**OpenAI TTS (Default)**
- Voices: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`
- Model: `tts-1` or `tts-1-hd`

**Cartesia (Optional)**
- Voice ID: configurable in `.env`
- Lower latency for real-time applications

## API Endpoints

- `GET /` - Serves the web UI
- `GET /ws` - WebSocket endpoint for voice streaming

## WebSocket Protocol

### Client → Server

```json
{
  "type": "input_audio_buffer.append",
  "audio": "base64_encoded_audio"
}
```

### Server → Client

```json
{
  "type": "user.transcript",
  "text": "User's transcribed message"
}
```

```json
{
  "type": "response.text",
  "text": "Agent's response"
}
```

```json
{
  "type": "response.audio.delta",
  "delta": "base64_encoded_audio"
}
```

## Development

### Project Structure

- **Clean Separation**: Config, agent logic, and schemas are separated
- **Type Safety**: All data validated with Pydantic v2
- **Async Throughout**: Fully async/await implementation
- **Minimal Dependencies**: Only essential packages included

### Adding Tools

To add tools to the agent, define them in `voice_agent.py`:

```python
@agent.define_tool
async def my_tool(context: RunContext, param: str) -> str:
    """Tool description"""
    # Implementation
    return result
```

### Testing

Run tests with pytest:

```bash
pytest -v --asyncio-mode=auto
```

## Troubleshooting

### Port Already in Use Error

If you see `[Errno 48] address already in use` when starting the server:

```bash
# Find the process using port 8084
lsof -ti:8084

# Kill the process (replace PID with the number from above)
kill -9 <PID>

# Or do it in one command
kill -9 $(lsof -ti:8084)

# Verify port is free (should show no output)
lsof -ti:8084
```

Then restart the server:

```bash
python main.py
```

### WebSocket Connection Issues
- Check browser console for errors
- Ensure server is running on correct port
- Verify firewall allows WebSocket connections

### Deepgram API Errors
- Verify API key is set correctly
- Check Deepgram dashboard for usage limits
- Ensure model name is valid (`nova-3`, `nova-2`, etc.)

### OpenAI API Errors
- Verify OpenAI API key has correct permissions
- Check API usage and billing status
- Ensure model name is valid (`gpt-4o-mini`, etc.)

## License

MIT

## Support

For issues or questions, check the Pydantic AI documentation:
- https://ai.pydantic.dev/
