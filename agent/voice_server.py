"""
Simple Deepgram + OpenAI Voice Agent
=====================================
Clean implementation using:
- Deepgram Streaming STT for real-time transcription
- OpenAI GPT-4 for conversation and function calling
- Deepgram TTS for voice responses
- Pulpoo API for task creation
"""

import asyncio
import json
import logging
import os
import base64
from datetime import datetime, timedelta
from typing import Optional
import websockets
import aiohttp
from dotenv import load_dotenv
import pytz

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")
load_dotenv(env_path)

# Configuration
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PULPOO_API_KEY = os.getenv("PULPOO_API_KEY")
PORT = int(os.getenv("PORT", 8084))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# System prompt for the agent
SYSTEM_PROMPT = """You are a professional phone support agent for Pulpoo Call Center.

Your job is to help customers report phone issues and create repair tasks.

Be warm, professional, and efficient. Keep responses under 40 words.

CONVERSATION FLOW:
1. Greet: "Hello! Thank you for calling Pulpoo. How can I help you with your phone today?"
2. Get issue: Ask what's wrong with their phone
3. Get contact: Ask for phone number and email
4. Confirm details: Repeat back what you heard
5. Create task: Use the create_task function with all details
6. Close: "Perfect! A technician will contact you within a few hours. Thank you!"

TASK DETAILS TO COLLECT:
- Issue summary (for title)
- Customer phone number
- Customer email
- Any additional details about the problem

Always assign tasks to: perezmd324@gmail.com
Set importance to: HIGH
Set canal to: Engineering"""

# OpenAI function definition
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Creates a repair task in Pulpoo. Call this after collecting customer's issue, phone number, and email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Brief summary of the phone issue (e.g., 'Cracked iPhone 14 screen')"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description including: issue details, customer phone number, and customer email"
                    }
                },
                "required": ["title", "description"]
            }
        }
    }
]


class VoiceAgent:
    """Simple voice agent session handler"""
    
    def __init__(self, websocket):
        self.websocket = websocket
        self.session_id = f"session_{id(websocket)}"
        self.conversation_history = []
        self.http_session = None
        self.deepgram_ws = None
        self.is_active = True
        self.is_speaking = False
        
    async def start(self):
        """Initialize and start the session"""
        try:
            logger.info(f"Starting session {self.session_id}")
            self.http_session = aiohttp.ClientSession()
            
            # Connect to Deepgram streaming STT
            await self._connect_deepgram_stt()
            
            # Send connection confirmation
            await self._send_to_client({
                "type": "session.connected",
                "session_id": self.session_id,
                "message": "Connected successfully"
            })
            
            # Send greeting
            await self._speak("Hello! Thank you for calling Pulpoo. How can I help you with your phone today?")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start session: {e}", exc_info=True)
            await self._send_to_client({
                "type": "error",
                "error": {"message": f"Failed to start: {str(e)}"}
            })
            return False
    
    async def _connect_deepgram_stt(self):
        """Connect to Deepgram streaming STT"""
        try:
            url = "wss://api.deepgram.com/v1/listen?model=nova-2&language=en-US&interim_results=false&punctuate=true&endpointing=500"
            headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
            
            self.deepgram_ws = await websockets.connect(url, additional_headers=headers)
            logger.info("Connected to Deepgram STT")
            
            # Start listening for transcripts
            asyncio.create_task(self._listen_deepgram())
            
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram STT: {e}")
            raise
    
    async def _listen_deepgram(self):
        """Listen for transcripts from Deepgram"""
        try:
            async for message in self.deepgram_ws:
                data = json.loads(message)
                
                # Check for transcript
                if data.get("type") == "Results":
                    channel = data.get("channel", {})
                    alternatives = channel.get("alternatives", [])
                    if alternatives:
                        transcript = alternatives[0].get("transcript", "").strip()
                        is_final = data.get("is_final", False)
                        
                        if is_final and transcript:
                            logger.info(f"User said: {transcript}")
                            await self._handle_user_input(transcript)
                            
        except websockets.exceptions.ConnectionClosed:
            logger.info("Deepgram connection closed")
        except Exception as e:
            logger.error(f"Error listening to Deepgram: {e}", exc_info=True)
    
    async def handle_audio(self, audio_data: bytes):
        """Forward audio to Deepgram for transcription"""
        try:
            if self.deepgram_ws and not self.deepgram_ws.closed:
                await self.deepgram_ws.send(audio_data)
        except Exception as e:
            logger.error(f"Error sending audio to Deepgram: {e}")
    
    async def _handle_user_input(self, transcript: str):
        """Process user input with OpenAI"""
        try:
            # Notify client
            await self._send_to_client({
                "type": "input_audio_buffer.speech_stopped"
            })
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": transcript
            })
            
            # Get response from OpenAI
            await self._get_openai_response()
            
        except Exception as e:
            logger.error(f"Error handling user input: {e}", exc_info=True)
            await self._speak("I'm sorry, I had trouble understanding. Could you repeat that?")
    
    async def _get_openai_response(self):
        """Get response from OpenAI"""
        try:
            # Prepare messages
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ] + self.conversation_history
            
            # Call OpenAI
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4",
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.7,
                "max_tokens": 150
            }
            
            async with self.http_session.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    message = result["choices"][0]["message"]
                    
                    # Check for tool calls
                    if message.get("tool_calls"):
                        await self._handle_tool_calls(message["tool_calls"])
                    else:
                        # Regular text response
                        text = message.get("content", "")
                        if text:
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": text
                            })
                            await self._speak(text)
                else:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error: {response.status} - {error_text}")
                    await self._speak("I'm having trouble processing your request. Could you please try again?")
                    
        except asyncio.TimeoutError:
            logger.error("OpenAI request timed out")
            await self._speak("Sorry, I'm taking too long to think. Please try again.")
        except Exception as e:
            logger.error(f"Error getting OpenAI response: {e}", exc_info=True)
            await self._speak("I apologize, but I encountered an error. Let's try again.")
    
    async def _handle_tool_calls(self, tool_calls: list):
        """Handle OpenAI function calls"""
        try:
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                function_name = function.get("name")
                
                if function_name == "create_task":
                    # Parse arguments
                    args = json.loads(function.get("arguments", "{}"))
                    
                    # Create task in Pulpoo
                    result = await self._create_pulpoo_task(
                        title=args.get("title", "Phone Repair Request"),
                        description=args.get("description", "")
                    )
                    
                    # Add tool call and response to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": json.dumps(result)
                    })
                    
                    # Get final response from OpenAI
                    await self._get_openai_response()
                    
        except Exception as e:
            logger.error(f"Error handling tool calls: {e}", exc_info=True)
            await self._speak("I had trouble creating the task. Let me try that again.")
    
    async def _create_pulpoo_task(self, title: str, description: str) -> dict:
        """Create task in Pulpoo via API"""
        try:
            # Calculate deadline (24 hours from now)
            deadline_dt = datetime.now(pytz.UTC) + timedelta(hours=24)
            deadline = deadline_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Prepare payload
            payload = {
                "title": title,
                "description": description,
                "assigned_to_email": "perezmd324@gmail.com",
                "deadline": deadline,
                "importance": "HIGH",
                "canal": "Engineering"
            }
            
            logger.info(f"Creating Pulpoo task: {title}")
            
            # Call Pulpoo API
            headers = {
                "X-API-Key": PULPOO_API_KEY,
                "Content-Type": "application/json"
            }
            
            async with self.http_session.post(
                "https://api.pulpoo.com/v1/external/tasks/create",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_text = await response.text()
                
                if response.status in [200, 201]:
                    logger.info("Task created successfully in Pulpoo")
                    return {
                        "success": True,
                        "message": "Task created successfully",
                        "title": title
                    }
                else:
                    logger.error(f"Failed to create Pulpoo task: {response.status} - {response_text}")
                    return {
                        "success": False,
                        "error": f"Failed to create task: {response.status}"
                    }
                    
        except Exception as e:
            logger.error(f"Exception creating Pulpoo task: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _speak(self, text: str):
        """Convert text to speech using Deepgram TTS"""
        try:
            logger.info(f"Speaking: {text}")
            
            self.is_speaking = True
            
            # Notify client that audio is starting
            await self._send_to_client({
                "type": "response.audio.start"
            })
            
            # Call Deepgram TTS
            url = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"
            headers = {
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {"text": text}
            
            async with self.http_session.post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    # Read audio data
                    audio_bytes = await response.read()
                    mime_type = response.headers.get("Content-Type", "audio/mpeg")
                    
                    # Convert to base64 and send to client
                    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                    await self._send_to_client({
                        "type": "response.audio.delta",
                        "delta": audio_b64,
                        "mime": mime_type
                    })
                    
                    # Notify audio is done
                    await self._send_to_client({
                        "type": "response.audio.done"
                    })
                else:
                    logger.error(f"TTS API error: {response.status}")
            
            self.is_speaking = False
            
        except Exception as e:
            logger.error(f"Error generating speech: {e}", exc_info=True)
            self.is_speaking = False
    
    async def _send_to_client(self, message: dict):
        """Send message to browser client"""
        try:
            if self.websocket and not self.websocket.closed:
                await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
    
    async def cleanup(self):
        """Clean up resources"""
        self.is_active = False
        
        # Close Deepgram connection
        if self.deepgram_ws:
            try:
                await self.deepgram_ws.close()
            except Exception as e:
                logger.error(f"Error closing Deepgram connection: {e}")
        
        # Close HTTP session
        if self.http_session and not self.http_session.closed:
            try:
                await self.http_session.close()
            except Exception as e:
                logger.error(f"Error closing HTTP session: {e}")
        
        logger.info(f"Session {self.session_id} cleaned up")


async def handle_client(websocket):
    """Handle WebSocket connection from browser"""
    session_id = f"session_{id(websocket)}"
    logger.info(f"New client connected: {session_id}")
    
    agent = VoiceAgent(websocket)
    
    try:
        # Start the agent
        if not await agent.start():
            return
        
        # Handle messages from client
        async for message in websocket:
            try:
                if isinstance(message, bytes):
                    # Binary audio data
                    await agent.handle_audio(message)
                else:
                    # JSON message
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    if message_type == "input_audio_buffer.append":
                        # Decode and forward audio
                        audio_b64 = data.get("audio", "")
                        audio_bytes = base64.b64decode(audio_b64)
                        await agent.handle_audio(audio_bytes)
                    
                    elif message_type == "ping":
                        await agent._send_to_client({"type": "pong"})
                        
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
            except Exception as e:
                logger.error(f"Error handling message: {e}", exc_info=True)
    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client {session_id} disconnected")
    except Exception as e:
        logger.error(f"Error in client handler: {e}", exc_info=True)
    finally:
        await agent.cleanup()


async def main():
    """Start the WebSocket server"""
    
    # Validate configuration
    if not DEEPGRAM_API_KEY:
        logger.error("DEEPGRAM_API_KEY must be set in .env file")
        return
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY must be set in .env file")
        return
    if not PULPOO_API_KEY:
        logger.error("PULPOO_API_KEY must be set in .env file")
        return
    
    logger.info(f"Starting Voice Agent Server on port {PORT}")
    logger.info("Technology: Deepgram STT + OpenAI GPT-4 + Deepgram TTS")
    
    async with websockets.serve(handle_client, "localhost", PORT, max_size=10485760):
        logger.info(f"✓ Server listening on ws://localhost:{PORT}")
        logger.info("Ready to accept connections!")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
