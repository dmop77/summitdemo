# Pulpoo Voice Assistant - Quick Start

Everything is set up! Here's how to get started:

## 1. Create Your `.env` File

In the `agent/` directory, create a `.env` file with your API keys:

```env
# Deepgram (Speech-to-Text)
DEEPGRAM_API_KEY=your_deepgram_key_here

# OpenAI (LLM & Text-to-Speech)
OPENAI_API_KEY=your_openai_key_here

# Pulpoo (Appointments)
PULPOO_API_KEY=your_pulpoo_key_here
PULPOO_API_URL=https://api.pulpoo.com/v1/external/tasks/create

# Server Config (Optional)
HOST=0.0.0.0
PORT=8084
DEBUG=false
```

## 2. Activate Virtual Environment

```bash
cd summitdemo
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

## 3. Run the Server

```bash
cd agent
python main.py
```

You should see:
```
INFO:__main__:Starting Voice Agent Server
INFO:__main__:✓ Server listening on http://0.0.0.0:8084
INFO:__main__:Ready to accept connections!
```

## 4. Open in Browser

Visit: **http://localhost:8084**

## 5. Use the Application

1. **Fill the form** with your name, email, and website URL
2. **Submit** - Your website will be scraped automatically
3. **Connect** to voice chat
4. **Speak naturally** - The agent will respond!

## What You Can Do

- ✅ Ask questions about your website
- ✅ Schedule appointments
- ✅ Have natural conversations
- ✅ Get website summaries

## Troubleshooting

**Problem**: "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

**Problem**: "API key not found"
- Check your `.env` file is in the `agent/` directory
- Make sure keys are spelled correctly

**Problem**: "Microphone not working"
- Check browser permissions (click lock icon in address bar)
- Try in a different browser

## Next Steps

- **Customize** the system prompt in `config.py`
- **Add new tools** in `agent_tools.py`
- **Deploy** using Docker or your platform
- **Read** the full `README.md` for details

## Architecture

```
Browser (input.html/chat.html)
    ↓ HTTP/WebSocket
Python Server (main.py)
    ↓
    ├─→ Deepgram (Speech-to-Text)
    ├─→ OpenAI (LLM + TTS)
    ├─→ Web Scraper
    └─→ Pulpoo (Appointments)
```

## Key Files

- `main.py` - Server (start here)
- `voice_agent.py` - AI agent logic
- `web_scraper.py` - Website parsing
- `agent_tools.py` - Tools for AI
- `config.py` - Settings

## Example Conversation

```
You:   "Hi, I'm interested in learning more"
Agent: "Hello! I've reviewed your website about [topic]. 
        How can I assist you today?"

You:   "I'd like to schedule a meeting"
Agent: "Absolutely! I have several times available next week.
        How about Tuesday at 2 PM?"

You:   "Perfect!"
Agent: "Great! I've scheduled your appointment. 
        You'll receive a confirmation at your email."
```

---

**Happy voice assisting!** 🎙️

For more details, see `SETUP_GUIDE.md` or `README.md`
