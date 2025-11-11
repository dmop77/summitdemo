# Voice Agent - Quick Start (2 Minutes)

Your friend sent you a voice AI agent. Here's how to use it.

## 📥 Setup (One Time Only)

**Mac/Linux:**
```bash
cd agent
./run.sh
```

**Windows:**
```bash
cd agent
run.bat
```

That's it! The script handles everything:
- ✅ Creates Python environment
- ✅ Installs dependencies  
- ✅ Starts the server

## 🚀 Using the Agent

Once you see:
```
✅ Server starting on http://localhost:8084
```

1. Open your browser to: `http://localhost:8084`
2. Click **"Connect"**
3. **Speak naturally** to the agent
4. The agent listens and responds
5. Click **"Disconnect"** when done

## 🔧 Troubleshooting

**"Address already in use"?**
```bash
# Mac/Linux: Kill the old process
lsof -ti:8084 | xargs kill -9

# Windows: Open Task Manager, find Python, End Task
```

**"No module named..."?**
- Close the terminal and run the script again
- Make sure you have Python 3.9+ installed

**Microphone not working?**
- Check browser microphone permissions
- Try a different browser (Chrome works best)

**Still having issues?**
- Contact your friend!

---

**Enjoy!** 🎤
