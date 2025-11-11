#!/bin/bash

# Setup Checker for Pulpoo Voice Agent
# =====================================
# Run this before starting to verify everything is ready

echo "🔍 Checking Pulpoo Voice Agent Setup"
echo "====================================="
echo ""

ERRORS=0
WARNINGS=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    ERRORS=$((ERRORS + 1))
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

# Check Python
echo "Checking dependencies..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python 3 installed: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.8 or higher"
fi

# Check if in right directory
if [ ! -f "agent/voice_server.py" ]; then
    print_error "Please run this script from the summitdemo directory"
    exit 1
fi
print_success "In correct directory"

# Check .env file
echo ""
echo "Checking configuration..."
if [ ! -f "agent/.env" ]; then
    print_error ".env file not found in agent/ directory"
    echo "  Create agent/.env with your API keys (see QUICKSTART.md)"
else
    print_success ".env file exists"
    
    # Check for API keys
    if grep -q "DEEPGRAM_API_KEY=" agent/.env && ! grep -q "DEEPGRAM_API_KEY=your-" agent/.env; then
        print_success "DEEPGRAM_API_KEY configured"
    else
        print_error "DEEPGRAM_API_KEY not configured or still has placeholder"
    fi
    
    if grep -q "OPENAI_API_KEY=" agent/.env && ! grep -q "OPENAI_API_KEY=sk-your-" agent/.env; then
        print_success "OPENAI_API_KEY configured"
    else
        print_error "OPENAI_API_KEY not configured or still has placeholder"
    fi
    
    if grep -q "PULPOO_API_KEY=" agent/.env && ! grep -q "PULPOO_API_KEY=cwz-your-" agent/.env; then
        print_success "PULPOO_API_KEY configured"
    else
        print_error "PULPOO_API_KEY not configured or still has placeholder"
    fi
fi

# Check virtual environment
echo ""
echo "Checking Python environment..."
if [ -d "agent/venv" ]; then
    print_success "Virtual environment exists"
    
    # Check if dependencies are installed
    if [ -f "agent/venv/bin/python" ]; then
        if agent/venv/bin/python -c "import deepgram" 2>/dev/null; then
            print_success "Dependencies installed (deepgram-sdk found)"
        else
            print_warning "Dependencies may not be installed. Run: pip install -r agent/requirements.txt"
        fi
    fi
else
    print_warning "Virtual environment not found. Will be created on first run"
fi

# Check port availability
echo ""
echo "Checking system..."
if lsof -Pi :8084 -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_warning "Port 8084 is already in use. Stop the existing process or use a different port"
else
    print_success "Port 8084 is available"
fi

# Check UI file
if [ -f "server/index.html" ]; then
    print_success "UI file exists"
else
    print_error "UI file (server/index.html) not found"
fi

# Summary
echo ""
echo "====================================="
echo "Summary:"
echo ""
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed!${NC}"
    echo ""
    echo "You're ready to start:"
    echo "  ./start.sh"
    echo ""
    echo "Then open server/index.html in your browser"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Setup is OK but has $WARNINGS warning(s)${NC}"
    echo ""
    echo "You can start the server, but check the warnings above"
    echo "  ./start.sh"
else
    echo -e "${RED}✗ Found $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    echo ""
    echo "Please fix the errors above before starting"
    echo ""
    echo "Quick fixes:"
    echo "  1. Create agent/.env with your API keys (see QUICKSTART.md)"
    echo "  2. Make sure you're in the summitdemo directory"
    echo "  3. Install Python 3.8+ if needed"
fi
echo ""

