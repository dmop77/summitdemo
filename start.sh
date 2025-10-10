#!/bin/bash

# Task Voice Agent Startup Script - OpenAI Realtime API
# =====================================================
# This script sets up and runs the Task Voice Agent with OpenAI Realtime API

set -e  # Exit on any error

echo "🎤 Task Voice Agent Setup - OpenAI Realtime API"
echo "==============================================="

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
if [ ! -f "setup.py" ]; then
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
if ! grep -q "sk-" agent/.env || ! grep -q "cwz" agent/.env; then
    print_warning "API keys not configured in agent/.env"
    print_status "Please edit agent/.env and add your actual API keys:"
    print_status "  - OPENAI_API_KEY: Your OpenAI API key (starts with sk-)"
    print_status "  - PULPOO_API_KEY: Your Pulpoo API key"
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
    pip install -r requirements.txt
    print_success "Dependencies installed"
    cd ..
else
    print_success "Virtual environment already active"
fi

# Function to cleanup background processes
cleanup() {
    print_status "Shutting down services..."
    jobs -p | xargs -r kill
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

print_status "Starting services..."

# Start authentication server in background
print_status "Starting authentication server..."
cd agent
source venv/bin/activate
python auth_server.py > auth_server.log 2>&1 &
AUTH_PID=$!
cd ..
sleep 2

# Start WebSocket server in background
print_status "Starting WebSocket server..."
cd agent
source venv/bin/activate
python realtime_server.py > realtime_server.log 2>&1 &
WEBSOCKET_PID=$!
cd ..
sleep 3

print_success "All services started!"
echo ""
echo "🌐 Web Interface: http://localhost:8082 (or open server/index.html)"
echo "🔐 Auth Server: http://localhost:8082"
echo "🔗 WebSocket Server: ws://localhost:8081"
echo ""
echo "📋 Services running:"
echo "  - Authentication Server (PID: $AUTH_PID)"
echo "  - WebSocket Server (PID: $WEBSOCKET_PID)"
echo ""
echo "📝 Logs:"
echo "  - Auth Server: agent/auth_server.log"
echo "  - WebSocket Server: agent/realtime_server.log"
echo ""
echo "🎯 Usage:"
echo "  1. Open http://localhost:8080 in your browser"
echo "  2. Click 'Connect' to start the voice agent"
echo "  3. Allow microphone access when prompted"
echo "  4. Speak naturally to create tasks"
echo ""
print_status "Press Ctrl+C to stop all services"

# Wait for user to stop
wait