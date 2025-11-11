# Pulpoo Voice Agent

Simple and reliable voice agent that creates tasks in Pulpoo using Deepgram for speech recognition, OpenAI for conversation processing, and Deepgram TTS for natural voice responses.

## Overview

- **Speech-to-Text**: Deepgram Nova-2 streaming STT for real-time transcription
- **AI Processing**: OpenAI GPT-4 for conversation understanding and function calling
- **Text-to-Speech**: Deepgram Aura-Asteria for natural voice responses
- **Task Creation**: Creates tasks in Pulpoo through conversational interface
- **Real-time Communication**: WebSocket-based audio streaming
- **Web Interface**: Beautiful, modern UI with animated orb

## Quick Start

```bash
# 1. Setup environment
cd agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure API keys
cd agent
touch .env
# Edit .env and add your API keys:
# OPENAI_API_KEY=sk-your-openai-key
# DEEPGRAM_API_KEY=your-deepgram-key
# PULPOO_API_KEY=cwz-your-pulpoo-key

# 3. Start system
cd ..
./start.sh

# 4. Open web interface
open server/index.html
```

## Requirements

```bash
deepgram-sdk>=3.8.0
openai>=1.50.0
python-dotenv>=1.0.0
aiohttp>=3.9.0
pydantic>=2.0.0
flask>=3.0.0
flask-cors>=4.0.0
pytz>=2023.3
websockets>=12.0
requests>=2.31.0
sounddevice>=0.4.6
numpy>=1.26.0
```

## API Keys Required

- **Deepgram API Key**: Get from [Deepgram Console](https://console.deepgram.com/signup) - Used for STT and TTS (includes $200 free credit)
- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys) - Used for GPT-4 conversation processing
- **Pulpoo API Key**: Get from your Pulpoo account - Used for task creation

Create a file `agent/.env` with your API keys:
```
DEEPGRAM_API_KEY=your-deepgram-key
OPENAI_API_KEY=sk-your-openai-key
PULPOO_API_KEY=cwz-your-pulpoo-key
```

## Services

- **Voice Agent Server** (Port 8084): WebSocket server using Deepgram STT + OpenAI + Deepgram TTS
- **Web Interface**: Open `server/index.html` in your browser

## Usage

1. Start system: `./start.sh`
2. Open web interface in browser
3. Click "Connect" to start voice agent
4. Allow microphone access
5. Speak to create tasks

## Task Assignment

Tasks are automatically assigned to: `perezmd324@gmail.com`

With HIGH importance and Engineering canal by default.

## Documentation

- **Setup Guide**: See `SETUP_INSTRUCTIONS.md` for detailed setup steps
- **Test Connection**: Run `python agent/test_deepgram_connection.py` to verify Deepgram setup

## Architecture

Simple and clean voice agent architecture:

```
User Audio → Deepgram STT (Streaming) → OpenAI GPT-4 → Deepgram TTS → Audio Output
                                              ↓
                                         Pulpoo API
```

**Key Features**:
1. **Deepgram Streaming STT** for real-time transcription
2. **OpenAI GPT-4** for conversation understanding and function calling
3. **Deepgram Aura TTS** for natural voice responses
4. **Pulpoo API** for task creation
5. **WebSocket** for real-time audio streaming
6. **Beautiful UI** with animated orb showing agent state