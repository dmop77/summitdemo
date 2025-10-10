# Pulpoo Voice Agent

Voice agent that creates tasks in Pulpoo using OpenAI Realtime API.

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
   python setup.py
   # Edit agent/.env with your actual API keys
   ```

3. **Run the agent:**
   ```bash
   cd agent
   source venv/bin/activate
   python task_agent.py dev
   ```

4. **Open web interface:**
   ```bash
   open server/index.html
   ```

## Usage

Speak naturally to create tasks:
- "Create a task to review the Q4 report by Friday"
- "I need to schedule a meeting with the team"

Tasks are automatically assigned to `cuevas@pulpoo.com` with HIGH priority.