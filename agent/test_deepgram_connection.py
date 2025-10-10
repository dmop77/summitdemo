"""
Test Deepgram API Connection
=============================
Quick test to verify Deepgram API credentials and basic functionality.
"""

import os
import asyncio
from dotenv import load_dotenv
from deepgram import DeepgramClient, SpeakOptions

# Load environment variables
load_dotenv(".env")

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")


async def test_deepgram_tts():
    """Test Deepgram Text-to-Speech."""
    print("🎤 Testing Deepgram TTS...")
    
    try:
        # Initialize client
        client = DeepgramClient(DEEPGRAM_API_KEY)
        
        # Configure TTS options
        options = SpeakOptions(
            model="aura-asteria-en",
            encoding="linear16",
            sample_rate=24000,
        )
        
        # Test text
        text = "Hello! This is a test of Deepgram text to speech. If you can hear this, the connection is working perfectly!"
        
        # Generate speech
        print(f"   Generating speech for: '{text[:50]}...'")
        response = client.speak.v("1").stream(
            {"text": text},
            options
        )
        
        # Collect audio
        audio_chunks = []
        for chunk in response.stream:
            if chunk:
                audio_chunks.append(chunk)
        
        audio_data = b''.join(audio_chunks)
        print(f"   ✓ Generated {len(audio_data)} bytes of audio")
        
        # Optionally save to file for testing
        output_file = "test_output.raw"
        with open(output_file, "wb") as f:
            f.write(audio_data)
        print(f"   ✓ Saved audio to {output_file}")
        print(f"   ℹ️  Play with: ffplay -f s16le -ar 24000 -ac 1 {output_file}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


async def test_deepgram_connection():
    """Test basic Deepgram API connection."""
    print("🔗 Testing Deepgram API Connection...")
    
    if not DEEPGRAM_API_KEY:
        print("   ✗ DEEPGRAM_API_KEY not found in environment")
        print("   ℹ️  Add it to agent/.env")
        return False
    
    print(f"   ✓ API Key found (length: {len(DEEPGRAM_API_KEY)})")
    
    try:
        client = DeepgramClient(DEEPGRAM_API_KEY)
        print("   ✓ Deepgram client initialized")
        return True
    except Exception as e:
        print(f"   ✗ Failed to initialize client: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Deepgram API Connection Test")
    print("="*60 + "\n")
    
    # Test 1: Basic connection
    connection_ok = await test_deepgram_connection()
    print()
    
    if not connection_ok:
        print("❌ Connection test failed. Please check your API key.\n")
        return
    
    # Test 2: TTS
    tts_ok = await test_deepgram_tts()
    print()
    
    # Summary
    print("="*60)
    if connection_ok and tts_ok:
        print("✅ All tests passed! Deepgram is ready to use.")
        print("\nNext steps:")
        print("  1. Run './start.sh' to start the voice agent")
        print("  2. Open server/index.html in your browser")
        print("  3. Click 'Connect' and start speaking")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("  • Verify DEEPGRAM_API_KEY in agent/.env")
        print("  • Check your Deepgram account has credits")
        print("  • Visit https://console.deepgram.com")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

