# Pulpoo Voice Agent

Voice agent that creates tasks in Pulpoo using OpenAI Realtime API with speech-to-speech architecture.

## Overview

- **Speech-to-Speech**: Direct audio processing using OpenAI's Realtime API
- **Task Creation**: Creates tasks in Pulpoo through conversational interface
- **Real-time Communication**: WebSocket-based audio streaming
- **Web Interface**: Modern UI for voice interaction

## Quick Start

```bash
# 1. Setup environment
cd agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure API keys
echo "OPENAI_API_KEY=sk-your-openai-key" > .env
echo "PULPOO_API_KEY=your-pulpoo-key" >> .env

# 3. Start system
cd ..
./start.sh

# 4. Open web interface
open server/index.html
```

## Requirements

```bash
openai>=1.50.0
python-dotenv>=1.0.0
aiohttp>=3.9.0
pydantic>=2.0.0
flask>=3.0.0
flask-cors>=4.0.0
pytz>=2023.3
websockets>=12.0
requests>=2.31.0
```

## API Keys Required

- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Pulpoo API Key**: Get from your Pulpoo account

## Services

- **Authentication Server** (Port 8082): Token generation and validation
- **Web Interface**: http://localhost:8080

## Usage

1. Start system: `./start.sh`
2. Open web interface in browser
3. Click "Connect" to start voice agent
4. Allow microphone access
5. Speak to create tasks

## Task Assignment

Tasks are automatically assigned to `cuevas@pulpoo.com` with HIGH priority by default.