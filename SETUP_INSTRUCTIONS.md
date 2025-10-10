# Pulpoo Voice Agent - Setup Instructions

## Quick Start

### 1. Install Dependencies

```bash
cd summitdemo/agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
```

### 2. Configure API Keys

Create a `.env` file in the `agent/` directory:

```bash
cd agent
touch .env
```

Edit `agent/.env` and add your API keys:

```bash
# OpenAI API (for LLM processing)
OPENAI_API_KEY=sk-your-actual-openai-key

# Deepgram API (for STT and TTS)
DEEPGRAM_API_KEY=your-actual-deepgram-key

# Pulpoo API (for task creation)
PULPOO_API_KEY=cwz-your-actual-pulpoo-key

# Optional
LOG_LEVEL=INFO
DEEPGRAM_SERVER_PORT=8084
```

### 3. Get Your API Keys

#### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

#### Deepgram API Key
1. Go to https://console.deepgram.com/signup
2. Sign up for a free account (includes $200 credit)
3. Go to API Keys section
4. Create a new API key
5. Copy the key

#### Pulpoo API Key
Contact your Pulpoo administrator for your API key.

### 4. Test the Setup

Test Deepgram connection:
```bash
cd agent
source venv/bin/activate
python test_deepgram_connection.py
cd ..
```

### 5. Start the Voice Agent

```bash
./start.sh
```

You should see:
```
🎯 Pulpoo Voice Agent is Ready!
═══════════════════════════════════════════════════════════════
🌐 Web Interface:
   Open server/index.html in your browser
```

### 6. Use the Voice Agent

1. Open `server/index.html` in your web browser
2. Click the "Connect" button
3. Allow microphone access when prompted
4. Start speaking naturally to create tasks

## Technology Stack

- **Speech-to-Text**: Deepgram Flux (flux-general-en) with turn detection
- **Text-to-Speech**: Deepgram Aura-Asteria voice
- **LLM Processing**: OpenAI GPT-4o with function calling
- **Task Management**: Pulpoo API
- **Audio**: WebSocket streaming (24kHz PCM16)

## Architecture

```
┌─────────────┐
│   Browser   │  (User speaks into microphone)
│  (WebRTC)   │
└──────┬──────┘
       │ WebSocket (audio stream)
       │
┌──────▼──────────────────────┐
│  voice_server.py            │
│  (Port 8084)                │
├─────────────────────────────┤
│  ┌─────────────────────┐   │
│  │ Flux STT            │   │  Speech → Text
│  │ (flux-general-en)   │   │  + Turn Detection
│  │ EndOfTurn Event     │   │  (knows when user done)
│  └─────────┬───────────┘   │
│            │ Transcript     │
│  ┌─────────▼───────────┐   │
│  │ OpenAI GPT-4o       │   │  Understanding
│  │ (LLM)               │   │  & Function Calling
│  └─────────┬───────────┘   │
│            │ Response       │
│  ┌─────────▼───────────┐   │
│  │ Deepgram TTS        │   │  Text → Speech
│  │ (Aura-Asteria)      │   │  (Streamed)
│  └─────────────────────┘   │
└─────────────┬───────────────┘
              │
┌─────────────▼───────────┐
│   Pulpoo API            │  Task Creation
│   (api.pulpoo.com)      │
└─────────────────────────┘
```

## Flux Voice Agent Pattern

This implementation uses the **EndOfTurn Only** pattern for simplicity:

- **StartOfTurn**: User starts speaking → Interrupt agent if speaking
- **EndOfTurn**: User finished speaking → Send to LLM and generate response
- **Update**: Interim transcripts (for reference only)

Benefits:
- Natural conversation flow with accurate turn detection
- User can interrupt agent at any time (barge-in)
- Lower latency than traditional VAD-based systems
- More control over the voice pipeline

## Conversation Flow

1. **User speaks**: "Hi, my iPhone screen is cracked"
2. **Deepgram STT**: Transcribes to text
3. **OpenAI GPT-4o**: Understands and generates response
4. **Deepgram TTS**: Converts response to speech
5. **Browser**: Plays audio response
6. **Repeat**: Until task is created

## Example Conversation

**Agent**: "Hello! Thank you for calling Pulpoo. How can I help you with your phone today?"

**User**: "My iPhone 14 screen is cracked and not responding to touch."

**Agent**: "I understand, your iPhone 14 screen is cracked. May I have a phone number where the technician can reach you?"

**User**: "Yes, 555-123-4567."

**Agent**: "Got it — 555-123-4567. And what's your email address?"

**User**: "john@example.com"

**Agent**: "Thank you. Just to confirm — the issue is a cracked iPhone 14 screen, your number is 555-123-4567, and your email is john@example.com. Is that correct?"

**User**: "Yes, that's correct."

**Agent**: "Perfect. I've got all the information I need. A technician will contact you within the next couple of hours."

*[Creates task in Pulpoo]*

**Agent**: "Your repair request has been created successfully. Thank you for calling Pulpoo!"

## Troubleshooting

### "DEEPGRAM_API_KEY not found"

Make sure you:
1. Created `agent/.env` file
2. Added your Deepgram API key
3. Key is on the correct line: `DEEPGRAM_API_KEY=your-key-here`

### "Failed to start Deepgram connection"

Check:
1. API key is valid
2. You have credits in your Deepgram account
3. Internet connection is working

### "Error processing with OpenAI"

Check:
1. OPENAI_API_KEY is correct
2. You have credits in your OpenAI account
3. Using a valid model (gpt-4o)

### "Task creation failed"

Check:
1. PULPOO_API_KEY is correct
2. Pulpoo API is accessible
3. Email addresses are valid

### Audio issues

**No transcription**:
- Check microphone permissions in browser
- Speak clearly and at normal volume
- Check browser console for errors

**No audio playback**:
- Check speaker/headphone volume
- Check browser audio permissions
- Try refreshing the page

### Port already in use

```bash
# Check what's using port 8081
lsof -i :8081

# Kill the process if needed
kill -9 <PID>
```

## Advanced Configuration

### Change TTS Voice

Edit `voice_server.py`, find the TTS connection line (~640):

```python
tts_connection = self.deepgram_client.speak.v1.connect(
    model="aura-2-asteria-en",  # Change this
    encoding="linear16",
    sample_rate=24000
)
```

Available voices:
- `aura-2-asteria-en` - Professional female (current)
- `aura-2-phoebe-en` - Warm female
- `aura-2-luna-en` - Smooth female
- `aura-2-stella-en` - Energetic female
- `aura-2-athena-en` - Confident female
- `aura-2-hera-en` - Clear female
- `aura-2-orion-en` - Professional male
- `aura-2-arcas-en` - Friendly male
- `aura-2-perseus-en` - Authoritative male
- `aura-2-angus-en` - Warm male
- `aura-2-orpheus-en` - Narrative male
- `aura-2-helios-en` - Confident male
- `aura-2-zeus-en` - Deep male

### Change STT Model

Edit `voice_server.py`, find the Flux connection line (~437):

```python
self.flux_connection = self.deepgram_client.listen.v2.connect(
    model="flux-general-en",  # Current: Flux with turn detection
    encoding="linear16",
    sample_rate=24000
)
```

Available Flux models:
- `flux-general-en` - Best turn detection (current)
- `nova-3` - High accuracy (if not using Flux features)

### Adjust Turn Detection

The Flux model has built-in turn detection - no manual configuration needed!
EndOfTurn events are automatically generated when the model detects the user has finished speaking.

## Logs

Logs are stored in `logs/` directory:

```bash
# View real-time logs
tail -f logs/voice_server.log

# Search for errors
grep ERROR logs/voice_server.log

# View last 50 lines
tail -50 logs/voice_server.log
```

## Stopping the Server

Press `Ctrl+C` in the terminal where `start.sh` is running.

The script will automatically clean up all processes.

## Cost Estimates

**Deepgram** (Pay-as-you-go after $200 credit):
- STT: ~$0.0043/minute
- TTS: ~$0.015/1000 characters

**OpenAI** (GPT-4o):
- Input: $2.50 per 1M tokens (~$0.01 per conversation)
- Output: $10.00 per 1M tokens (~$0.03 per conversation)

**Typical 5-minute call**:
- Deepgram STT: $0.02
- Deepgram TTS: $0.08  
- OpenAI: $0.05
- **Total: ~$0.15 per call**

## Support

- Deepgram Docs: https://developers.deepgram.com
- OpenAI Docs: https://platform.openai.com/docs
- Pulpoo Support: Contact your administrator

## Next Steps

1. ✅ Install dependencies
2. ✅ Configure API keys
3. ✅ Test connection
4. ✅ Start server
5. ✅ Make your first call!

For migration from OpenAI Realtime API, see `MIGRATION_TO_DEEPGRAM.md`.

