#!/bin/bash

# Task Voice Agent Startup Script - Deepgram STT/TTS with OpenAI Processing
# ===========================================================================
# This script sets up and runs the Task Voice Agent with Deepgram for voice

set -e  # Exit on any error

echo "🎤 Pulpoo Voice Agent - Simple & Reliable"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "agent/voice_server.py" ]; then
    print_error "Please run this script from the summitdemo directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f "agent/.env" ]; then
    print_warning ".env file not found. Creating from template..."
    if [ -f "agent/.env.template" ]; then
        cp agent/.env.template agent/.env
        print_success "Created .env file from template"
        print_warning "Please edit agent/.env and add your API keys before continuing"
        print_status "Required keys: OPENAI_API_KEY, PULPOO_API_KEY"
        exit 1
    else
        print_error ".env.template not found. Please create agent/.env manually"
        exit 1
    fi
fi

# Check if API keys are set
if ! grep -q "DEEPGRAM_API_KEY=" agent/.env || ! grep -q "OPENAI_API_KEY=" agent/.env || ! grep -q "PULPOO_API_KEY=" agent/.env; then
    print_warning "API keys not configured in agent/.env"
    print_status "Please edit agent/.env and add your actual API keys:"
    print_status "  - DEEPGRAM_API_KEY: Your Deepgram API key (for STT & TTS)"
    print_status "  - OPENAI_API_KEY: Your OpenAI API key (starts with sk-)"
    print_status "  - PULPOO_API_KEY: Your Pulpoo API key (starts with cwz-)"
    print_status ""
    print_status "Example agent/.env file:"
    print_status "  DEEPGRAM_API_KEY=your-deepgram-key"
    print_status "  OPENAI_API_KEY=sk-your-openai-key"
    print_status "  PULPOO_API_KEY=cwz-your-pulpoo-key"
    exit 1
fi

print_success "Environment configuration looks good!"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Check if we're in a virtual environment or create one
if [ -z "$VIRTUAL_ENV" ]; then
    print_status "Setting up Python virtual environment..."
    cd agent
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Created virtual environment"
    fi
    
    source venv/bin/activate
    print_success "Activated virtual environment"
    
    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install -q -r requirements.txt
    print_success "Dependencies installed"
    cd ..
else
    print_success "Virtual environment already active"
fi

# Function to cleanup background processes
cleanup() {
    print_status "Shutting down services..."
    if [ ! -z "$DEEPGRAM_PID" ] && kill -0 $DEEPGRAM_PID 2>/dev/null; then
        kill $DEEPGRAM_PID
    fi
    print_success "All services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM EXIT

print_status "Starting services..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Start voice server
print_status "Starting voice agent server on port 8084..."
cd agent
source venv/bin/activate
python voice_server.py > ../logs/voice_server.log 2>&1 &
DEEPGRAM_PID=$!
cd ..
sleep 3

# Check if voice server started successfully
if ! kill -0 $DEEPGRAM_PID 2>/dev/null; then
    print_error "Voice server failed to start. Check logs/voice_server.log"
    exit 1
fi
print_success "Voice server started (PID: $DEEPGRAM_PID)"

print_success "All services started successfully!"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "🎯 Pulpoo Voice Agent is Ready!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "🌐 Web Interface:"
echo "   Open server/index.html in your browser"
echo "   (Use a local web server for best results)"
echo ""
echo "🔗 Service Endpoints:"
echo "   • Voice Server: ws://localhost:8084"
echo ""
echo "📋 Running Services:"
echo "   • Voice Server (PID: $DEEPGRAM_PID)"
echo ""
echo "📝 Log Files:"
echo "   • Voice Server: logs/voice_server.log"
echo ""
echo "🎯 Quick Start:"
echo "   1. Open server/index.html in your browser"
echo "   2. Click 'Connect' to start the voice agent"
echo "   3. Allow microphone access when prompted"
echo "   4. Speak naturally to create tasks in Pulpoo"
echo ""
echo "💡 Technology Stack:"
echo "   ✓ Deepgram Nova-2 Streaming STT (Speech-to-Text)"
echo "   ✓ OpenAI GPT-4 (Conversation Processing + Function Calling)"
echo "   ✓ Deepgram Aura TTS (Natural Voice Responses)"
echo "   ✓ Pulpoo API (Task Creation)"
echo "   ✓ Real-time WebSocket audio streaming"
echo "   ✓ Beautiful animated UI"
echo ""
echo "🐛 Troubleshooting:"
echo "   • Check logs/voice_server.log for error messages"
echo "   • Verify API keys in agent/.env are correct"
echo "   • Ensure port 8084 is available"
echo "   • Test API connection: python agent/test_pulpoo_connection.py"
echo ""
echo "═══════════════════════════════════════════════════════════════"
print_status "Press Ctrl+C to stop all services"
echo ""

# Monitor services
while true; do
    sleep 5
    
    # Check if service is still running
    if ! kill -0 $DEEPGRAM_PID 2>/dev/null; then
        print_error "Voice server died unexpectedly!"
        print_status "Check logs/voice_server.log for details"
        cleanup
    fi
done