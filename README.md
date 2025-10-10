# Pulpoo Voice Agent - OpenAI Realtime API

Voice agent that creates tasks in Pulpoo using OpenAI Realtime API with speech-to-speech architecture.

## Features

- **Speech-to-Speech Architecture**: Direct audio processing using OpenAI's Realtime API
- **Natural Conversation**: Handles voice input and responds with natural speech
- **Task Creation**: Creates tasks in Pulpoo through conversational interface
- **Real-time Communication**: WebSocket-based real-time audio streaming
- **Modern Web Interface**: Beautiful, responsive web UI with visual feedback

## Architecture

This implementation uses OpenAI's Realtime API with the speech-to-speech architecture:

- **Audio Input**: Captures user speech through browser microphone
- **Real-time Processing**: Streams audio to OpenAI Realtime API
- **Natural Responses**: Agent responds with natural speech output
- **Task Integration**: Creates tasks in Pulpoo via API calls

## Components

The system consists of these core components:

1. **Voice Agent** (`agent/voice_agent.py`) - Core agent using OpenAI Realtime API
2. **WebSocket Server** (`agent/realtime_server.py`) - Real-time communication handler
3. **Authentication Server** (`agent/auth_server.py`) - Token-based authentication
4. **Web Interface** (`server/index.html`) - Modern web UI for voice interaction
5. **Startup Script** (`start.sh`) - Automated service orchestration

## Setup

1. **Install dependencies:**
   ```bash
   cd agent
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure API keys:**
   ```bash
   cp agent/.env.template agent/.env
   # Edit agent/.env with your actual API keys
   ```

3. **Run the complete system:**
   ```bash
   ./start.sh
   ```

4. **Open web interface:**
   ```bash
   open server/index.html
   # Or visit: http://localhost:8082
   ```

## Usage

1. **Start the system** using `./start.sh`
2. **Open the web interface** in your browser
3. **Click "Connect"** to start the voice agent
4. **Allow microphone access** when prompted
5. **Speak naturally** to create tasks:
   - "Create a task to review the Q4 report by Friday"
   - "I need to schedule a meeting with the team"
   - "Add a high priority task to update the website"

## API Keys Required

- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Pulpoo API Key**: Get from your Pulpoo account

## Services

The system runs these services:

- **Authentication Server** (Port 8082): Handles token generation and validation
- **WebSocket Server** (Port 8081): Manages real-time communication with OpenAI Realtime API
- **Web Interface**: Provides the user interface for voice interaction

## Task Assignment

Tasks are automatically assigned to `cuevas@pulpoo.com` with HIGH priority by default.