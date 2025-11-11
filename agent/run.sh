#!/bin/bash

# Simple script to run the voice agent

echo "🚀 Starting Simplified Voice Agent..."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "📥 Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
    echo ""
fi

# Activate venv
source venv/bin/activate

# Start the server
echo "✅ Server starting on http://localhost:8084"
echo "📢 Open your browser and go to http://localhost:8084"
echo "🛑 Press Ctrl+C to stop"
echo ""
python3 simple_voice_agent.py
