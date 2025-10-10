#!/usr/bin/env python3
"""
Setup script for Pulpoo Voice Agent
===================================
Helps users configure the voice agent with their API keys.
"""

import os
import sys
from pathlib import Path

def main():
    """Main setup function."""
    print("🎤 Pulpoo Voice Agent Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("agent").exists():
        print("❌ Please run this script from the summitdemo directory")
        sys.exit(1)
    
    env_file = Path("agent/.env")
    env_template = Path("agent/.env.template")
    
    # Check if .env already exists
    if env_file.exists():
        print("✅ .env file already exists")
        response = input("Do you want to reconfigure it? (y/N): ").strip().lower()
        if response != 'y':
            print("Setup complete!")
            return
    
    # Create .env from template if it doesn't exist
    if not env_file.exists() and env_template.exists():
        print("📝 Creating .env file from template...")
        with open(env_template, 'r') as f:
            content = f.read()
        with open(env_file, 'w') as f:
            f.write(content)
        print("✅ Created .env file")
    
    # Get API keys from user
    print("\n🔑 API Key Configuration")
    print("-" * 25)
    
    # OpenAI API Key
    print("\n1. OpenAI API Key")
    print("   Get your API key from: https://platform.openai.com/api-keys")
    openai_key = input("   Enter your OpenAI API key (starts with sk-): ").strip()
    
    if not openai_key.startswith("sk-"):
        print("❌ Invalid OpenAI API key format")
        sys.exit(1)
    
    # Pulpoo API Key
    print("\n2. Pulpoo API Key")
    print("   Get your API key from your Pulpoo account")
    pulpoo_key = input("   Enter your Pulpoo API key (starts with cwz): ").strip()
    
    if not pulpoo_key.startswith("cwz"):
        print("❌ Invalid Pulpoo API key format")
        sys.exit(1)
    
    # Update .env file
    print("\n💾 Saving configuration...")
    try:
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Replace placeholder values
        content = content.replace("sk-your-openai-api-key-here", openai_key)
        content = content.replace("cwz-your-pulpoo-api-key-here", pulpoo_key)
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        print("✅ Configuration saved successfully!")
        
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        sys.exit(1)
    
    # Final instructions
    print("\n🎉 Setup Complete!")
    print("=" * 20)
    print("\nNext steps:")
    print("1. Run './start.sh' to start the voice agent")
    print("2. Open http://localhost:8080 in your browser")
    print("3. Click 'Connect' to start using the voice agent")
    print("\nFor more information, see README.md")

if __name__ == "__main__":
    main()