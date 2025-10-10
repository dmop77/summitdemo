#!/usr/bin/env python3
"""Simple setup for Pulpoo Voice Agent"""

import os

def main():
    print("🎤 Pulpoo Voice Agent Setup")
    print("=" * 30)
    
    # Create .env file
    env_content = """# Pulpoo Voice Agent Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
PULPOO_API_KEY=your-pulpoo-api-key-here
LOG_LEVEL=INFO
"""
    
    env_path = "agent/.env"
    with open(env_path, "w") as f:
        f.write(env_content)
    
    print(f"✅ Created {env_path}")
    print("📝 Please edit the file and add your actual API keys:")
    print("   - OPENAI_API_KEY: Your OpenAI API key")
    print("   - PULPOO_API_KEY: Your Pulpoo API key")
    print()
    print("🚀 Then run: cd agent && uv run python task_agent.py dev")

if __name__ == "__main__":
    main()
