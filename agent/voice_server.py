"""
Deepgram Flux Voice Agent Server
==================================
WebSocket server using Flux STT with advanced turn detection,
OpenAI for LLM processing, and Deepgram TTS for natural voice responses.

Architecture:
Browser → Flux STT (turn detection) → OpenAI GPT-4o → Deepgram TTS → Browser
"""

import asyncio
import json
import logging
import os
import base64
import struct
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import websockets
import aiohttp
from dotenv import load_dotenv
# Using direct HTTP API calls instead of SDK
import pytz
import threading

# Load environment variables from the same directory as this script
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")
load_dotenv(env_path)

# Configuration
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PULPOO_API_KEY = os.getenv("PULPOO_API_KEY")
PORT = int(os.getenv("DEEPGRAM_SERVER_PORT", 8084))

# Explicitly set DEEPGRAM_API_KEY in os.environ for DeepgramClient to find
if DEEPGRAM_API_KEY:
    os.environ["DEEPGRAM_API_KEY"] = DEEPGRAM_API_KEY

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Agent instructions
AGENT_INSTRUCTIONS = """# Personality and Tone
## Identity
You are a professional English-speaking voice assistant for Pulpoo Call Center. 
Your job is to help customers report phone issues and create tasks for technicians to follow up.

## Demeanor
Professional, polite, clear, and efficient. 
You sound calm and reassuring, using neutral pronunciation. 
You are always respectful and helpful.

## Tone
Warm, confident, and natural — not robotic. 
You speak clearly and never rush the customer.

## Level of Enthusiasm
Professional and steady — never overly excited, but friendly.

## Level of Formality
Professional and approachable.

## Level of Emotion
Calm and empathetic. You acknowledge the customer's issue clearly.

## Filler Words
You may use light fillers such as "okay" or "alright" naturally, but keep them minimal.

## Pacing
Steady, clear, and easy to follow.

# Instructions
- The purpose of the call is to **collect all relevant details about the customer's phone issue** and **create a repair task** in Pulpoo.
- Speak naturally and professionally.
- Keep your responses concise and under 50 words. Be direct and to the point.
- Never ask about assignment — all tasks are automatically assigned to cuevas@pulpoo.com, efernandez@pulpoo.com, and perezmd324@gmail.com.
- Always confirm key details with the customer before creating the task.
- If the customer spells out a name, phone number, or email, repeat it back for confirmation.
- Once all details are confirmed, say: 
  "Perfect. I've got all the information I need. A technician will contact you within the next couple of hours."
- Then call the task creation tool with the collected details.
- If the API returns an error, explain it clearly and offer to retry.
- NEVER read out loud IDs, serial numbers, or very large numbers to users.
- Use natural, conversational language that's easy to understand when spoken aloud.

# Task Information to Collect
REQUIRED:
- **Title**: A clear and short summary of the issue (e.g., "Cracked iPhone 14 screen")
- **Customer Phone Number**: Required so the technician can follow up
- **Customer Email Address**: Required for communication confirmation

OPTIONAL (Ask if not provided):
- **Description**: Extra details about the issue (e.g., "the screen is flickering and not responding to touch")
- **Deadline**: Defaults to 24 hours if not provided
- **Importance**: Defaults to HIGH

ASSIGNMENT:
- Assigned to cuevas@pulpoo.com, efernandez@pulpoo.com, and perezmd324@gmail.com
- Importance = HIGH if not specified

# Conversation Flow
1. **Greeting**
   - Example: "Hello! Thank you for calling Pulpoo. How can I help you with your phone today?"

2. **Issue Identification**
   - Ask: "Can you tell me what's going on with your phone?"
   - Listen carefully and extract the **main issue** for the task title.

3. **Collect Contact Details**
   - Ask: "May I please have a good phone number to reach you?" 
     → Repeat the number to confirm.
   - Ask: "And could I also get your email address?" 
     → Repeat it to confirm.

4. **Additional Details (Optional)**
   - If needed: "Can you give me a few more details about the issue?"
   - Get any extra description the customer wants to provide.

5. **Confirmation**
   - Summarize all details back:
     "Just to confirm — the issue is [title], the phone number is [number], and the email is [email]. Is that correct?"

6. **Closure**
   - Say: "Perfect. I've got all the information I need. A technician will contact you within the next couple of hours."

7. **Create Task**
   - Use the tool to create a task with:
     - Title = short issue summary
     - Description = additional issue details + phone number + email
     - Deadline = default 24 hours if not specified
     - Importance = HIGH
     - Assigned to cuevas@pulpoo.com, efernandez@pulpoo.com, and perezmd324@gmail.com

8. **Success Message**
   - Say: "Your repair request has been created successfully. Thank you for calling Pulpoo!"

# Example Dialog
Customer: "Hi, my phone screen cracked this morning."
Agent: "Okay, I understand. So your phone screen is cracked. May I have a phone number where the technician can reach you?"
Customer: "Yes, 555-123-4567."
Agent: "Got it — 555-123-4567. And what's your email address?"
Customer: "john@example.com."
Agent: "Thank you. So the issue is a cracked phone screen, your number is 555-123-4567, and your email is john@example.com. Is that correct?"
Customer: "Yes."
Agent: "Perfect. I've got all the information I need. A technician will contact you within the next couple of hours."
[Calls create_task function with collected details]

# Error Handling
- If task creation fails: "Hmm, something went wrong on my end. Let's try that again."
"""

# Tool definitions for OpenAI
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Creates a new task in the Pulpoo system with the provided details. This should be called after collecting all necessary information from the customer including title, phone number, and email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_name": {
                        "type": "string",
                        "description": "A clear, concise title for the task (e.g., 'Cracked iPhone 14 screen')"
                    },
                    "task_description": {
                        "type": "string",
                        "description": "Detailed description of the issue including customer phone number and email address"
                    },
                    "assignee": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of email addresses to assign the task to. Always use: ['cuevas@pulpoo.com', 'efernandez@pulpoo.com', 'perezmd324@gmail.com']"
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Project ID in Pulpoo. Use 'PRO-1' as default."
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date in ISO format. Defaults to 24 hours from now if not specified."
                    }
                },
                "required": ["task_name", "task_description", "assignee"]
            }
        }
    }
]


async def create_task_tool(
    task_name: str,
    task_description: str,
    assignee: list,
    project_id: str = "PRO-1",
    due_date: Optional[str] = None,
    http_session: Optional[aiohttp.ClientSession] = None
) -> dict:
    """
    Create a task in Pulpoo via API.
    
    Args:
        task_name: Title of the task
        task_description: Detailed description
        assignee: List of email addresses to assign to
        project_id: Pulpoo project ID
        due_date: ISO format due date (defaults to 24 hours from now)
        http_session: aiohttp session to reuse
        
    Returns:
        dict with success status and task details or error message
    """
    try:
        # Calculate default due date if not provided (24 hours from now in GMT-5)
        if not due_date:
            gmt_minus_5 = pytz.timezone('America/New_York')  # GMT-5
            now = datetime.now(gmt_minus_5)
            due_datetime = now + timedelta(hours=24)
            due_date = due_datetime.isoformat()
        
        # Prepare task data
        task_data = {
            "name": task_name,
            "description": task_description,
            "projectId": project_id,
            "assignedTo": assignee,
            "dueDate": due_date,
            "importance": "HIGH",
            "status": "pending"
        }
        
        logger.info(f"Creating task: {task_name}")
        logger.debug(f"Task data: {task_data}")
        
        # Make API request
        pulpoo_url = "https://www.pulpoo.com/api/v1/tasks"
        headers = {
            "Authorization": f"Bearer {PULPOO_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Use provided session or create new one
        should_close = False
        if not http_session:
            http_session = aiohttp.ClientSession()
            should_close = True
        
        try:
            async with http_session.post(pulpoo_url, json=task_data, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 201:
                    result = json.loads(response_text)
                    logger.info(f"Task created successfully: {result.get('id')}")
                    return {
                        "success": True,
                        "message": "Task created successfully",
                        "task_id": result.get("id"),
                        "task_name": task_name
                    }
                else:
                    logger.error(f"Failed to create task: {response.status} - {response_text}")
                    return {
                        "success": False,
                        "error": f"Failed to create task: {response.status}",
                        "details": response_text
                    }
        finally:
            if should_close:
                await http_session.close()
                
    except Exception as e:
        logger.error(f"Exception creating task: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "message": "An error occurred while creating the task"
        }


class FluxVoiceSession:
    """Manages a voice session using Flux STT + OpenAI + Deepgram TTS."""
    
    def __init__(self, websocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.http_session = None
        
        # State management
        self.is_active = True
        self.is_speaking = False
        self.conversation_history: List[Dict] = []
        self.current_transcript = ""
        self.greeting_sent = False
        
        # Tasks
        self.tts_queue = asyncio.Queue()
        self.tts_task = None
        
    async def initialize(self):
        """Initialize session."""
        try:
            self.http_session = aiohttp.ClientSession()
            
            # Start TTS processor
            self.tts_task = asyncio.create_task(self._process_tts_queue())
            
            logger.info(f"Session {self.session_id} initialized")
            
            # Notify client
            await self.send_to_client({
                "type": "session.connected",
                "session_id": self.session_id,
                "message": "Connected successfully"
            })
            
            # Send greeting
            await self._send_greeting()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            import traceback
            traceback.print_exc()
            await self.send_to_client({
                "type": "error",
                "error": {"message": f"Failed to initialize: {str(e)}"}
            })
            return False
    
    async def _handle_start_of_turn(self):
        """Handle user starting to speak (potential interruption)."""
        try:
            # Notify client
            await self.send_to_client({
                "type": "input_audio_buffer.speech_started"
            })
            
            # If agent is speaking, interrupt it
            if self.is_speaking:
                logger.info("User interrupted agent - stopping TTS")
                await self._stop_speaking()
                
        except Exception as e:
            logger.error(f"Error handling start of turn: {e}")
    
    async def _handle_end_of_turn(self, transcript: str):
        """Handle user finished speaking (process with LLM)."""
        try:
            logger.info(f"End of turn - Transcript: {transcript}")
            
            # Notify client
            await self.send_to_client({
                "type": "input_audio_buffer.speech_stopped"
            })
            
            if not transcript:
                return
            
            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": transcript
            })
            
            # Process with OpenAI
            await self._process_with_openai()
            
        except Exception as e:
            logger.error(f"Error handling end of turn: {e}")
    
    async def _process_with_openai(self):
        """Send conversation to OpenAI and get response."""
        try:
            logger.info("Processing with OpenAI...")
            
            # Prepare messages
            messages = [
                {"role": "system", "content": AGENT_INSTRUCTIONS}
            ] + self.conversation_history
            
            # Call OpenAI API
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.7,
                "max_tokens": 150
            }
            
            async with self.http_session.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    choice = result["choices"][0]
                    message = choice["message"]
                    
                    # Check if there's a tool call
                    if message.get("tool_calls"):
                        await self._handle_tool_calls(message["tool_calls"])
                        # After tool execution, get assistant's response
                        return
                    
                    # Get assistant's text response
                    assistant_text = message.get("content", "")
                    if assistant_text:
                        logger.info(f"Assistant response: {assistant_text}")
                        
                        # Add to history
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": assistant_text
                        })
                        
                        # Convert to speech
                        await self._speak(assistant_text)
                else:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error: {response.status} - {error_text}")
                    await self._speak("I'm having trouble processing your request. Could you please try again?")
                    
        except Exception as e:
            logger.error(f"Error processing with OpenAI: {e}")
            import traceback
            traceback.print_exc()
            await self._speak("I apologize, but I encountered an error. Let's try again.")
    
    async def _handle_tool_calls(self, tool_calls: List[Dict]):
        """Handle OpenAI tool/function calls."""
        try:
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                function_name = function.get("name")
                
                if function_name == "create_task":
                    # Parse arguments
                    args_str = function.get("arguments", "{}")
                    args = json.loads(args_str)
                    
                    logger.info(f"Creating task with args: {args}")
                    
                    # Call task creation function
                    result = await create_task_tool(
                        task_name=args.get("task_name"),
                        task_description=args.get("task_description"),
                        assignee=args.get("assignee"),
                        project_id=args.get("project_id", "PRO-1"),
                        due_date=args.get("due_date"),
                        http_session=self.http_session
                    )
                    
                    # Add tool call to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    
                    # Add tool response to history
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": json.dumps(result)
                    })
                    
                    # Get final response from OpenAI
                    await self._process_with_openai()
                    
        except Exception as e:
            logger.error(f"Error handling tool calls: {e}")
            import traceback
            traceback.print_exc()
    
    async def _speak(self, text: str):
        """Convert text to speech and stream to client."""
        try:
            logger.info(f"Speaking: {text}")
            
            # Add to TTS queue
            await self.tts_queue.put(text)
            
        except Exception as e:
            logger.error(f"Error queuing speech: {e}")
    
    async def _process_tts_queue(self):
        """Process TTS requests from queue."""
        while self.is_active:
            try:
                # Get next text to speak
                text = await asyncio.wait_for(self.tts_queue.get(), timeout=1.0)
                
                # Generate and stream TTS
                await self._generate_tts(text)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing TTS queue: {e}")
    
    async def _generate_tts(self, text: str):
        """Generate TTS audio using Deepgram API directly."""
        try:
            self.is_speaking = True
            
            # Notify client that audio is starting
            await self.send_to_client({
                "type": "response.audio.start"
            })
            
            # Use Deepgram TTS API directly (like your working example)
            url = "https://api.deepgram.com/v1/speak?model=aura-2-asteria-en"
            headers = {
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {"text": text}
            
            async with self.http_session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    audio_bytes = await response.read()
                    
                    if self.is_speaking:  # Check if not interrupted
                        # Convert to base64 and send
                        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                        await self.send_to_client({
                            "type": "response.audio.delta",
                            "delta": audio_b64
                        })
                        
                        # Send done
                        await self.send_to_client({
                            "type": "response.audio.done"
                        })
                else:
                    logger.error(f"TTS API error: {response.status}")
            
            self.is_speaking = False
            
        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
            import traceback
            traceback.print_exc()
            self.is_speaking = False
    
    async def _stop_speaking(self):
        """Stop current speech (for interruptions)."""
        self.is_speaking = False
        # Clear TTS queue
        while not self.tts_queue.empty():
            try:
                self.tts_queue.get_nowait()
            except:
                break
    
    async def _send_greeting(self):
        """Send initial greeting."""
        if not self.greeting_sent:
            self.greeting_sent = True
            greeting = "Hello! Thank you for calling Pulpoo. How can I help you with your phone today?"
            self.conversation_history.append({
                "role": "assistant",
                "content": greeting
            })
            await self._speak(greeting)
    
    async def handle_audio(self, audio_data: bytes):
        """Process audio with Deepgram STT."""
        try:
            # Store audio for processing
            if not hasattr(self, 'audio_buffer'):
                self.audio_buffer = b''
            self.audio_buffer += audio_data
            
            # Process when we have enough audio (simulate EndOfTurn after 2 seconds of silence)
            if not hasattr(self, 'last_audio_time'):
                self.last_audio_time = asyncio.get_event_loop().time()
            
            current_time = asyncio.get_event_loop().time()
            if current_time - self.last_audio_time > 2.0 and self.audio_buffer:
                # Process accumulated audio
                await self._process_audio_buffer()
                self.audio_buffer = b''
            
            self.last_audio_time = current_time
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
    
    async def _process_audio_buffer(self):
        """Process accumulated audio buffer with Deepgram STT."""
        try:
            if not self.audio_buffer:
                return
                
            logger.info(f"Processing audio buffer: {len(self.audio_buffer)} bytes")
            
            # Use Deepgram STT API directly (like your working example)
            url = "https://api.deepgram.com/v1/listen?model=nova-2&language=en-US"
            headers = {
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "audio/wav"
            }
            
            async with self.http_session.post(url, headers=headers, data=self.audio_buffer) as response:
                if response.status == 200:
                    result = await response.json()
                    transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
                    
                    if transcript.strip():
                        logger.info(f"Transcript: {transcript}")
                        await self._handle_end_of_turn(transcript.strip())
                else:
                    logger.error(f"STT API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error processing audio buffer: {e}")
            import traceback
            traceback.print_exc()
    
    async def send_to_client(self, message: dict):
        """Send message to browser client."""
        try:
            if self.websocket and self.websocket.open:
                await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        self.is_active = False
        
        # Stop tasks
        if self.tts_task:
            self.tts_task.cancel()
        
        # Close HTTP session
        if self.http_session and not self.http_session.closed:
            try:
                await self.http_session.close()
            except Exception as e:
                logger.error(f"Error closing HTTP session: {e}")
        
        logger.info(f"Session {self.session_id} cleaned up")


async def handle_client(websocket):
    """Handle WebSocket connection from browser client."""
    session_id = f"session_{id(websocket)}"
    logger.info(f"New client connected: {session_id}")
    
    session = FluxVoiceSession(websocket, session_id)
    
    try:
        if not await session.initialize():
            return
        
        # Handle messages from client
        async for message in websocket:
            try:
                if isinstance(message, bytes):
                    # Binary audio data
                    await session.handle_audio(message)
                else:
                    # JSON message
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    if message_type == "input_audio_buffer.append":
                        # Decode base64 audio
                        audio_b64 = data.get("audio", "")
                        audio_bytes = base64.b64decode(audio_b64)
                        await session.handle_audio(audio_bytes)
                    
                    elif message_type == "ping":
                        await session.send_to_client({"type": "pong"})
                        
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
            except Exception as e:
                logger.error(f"Error handling message: {e}")
    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client {session_id} disconnected")
    except Exception as e:
        logger.error(f"Error in client handler: {e}")
    finally:
        await session.cleanup()


async def main():
    """Start the WebSocket server."""
    
    # Validate configuration
    if not DEEPGRAM_API_KEY:
        logger.error("DEEPGRAM_API_KEY must be set in environment")
        return
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY must be set in environment")
        return
    if not PULPOO_API_KEY:
        logger.error("PULPOO_API_KEY must be set in environment")
        return
    
    logger.info(f"Starting Flux Voice Server on port {PORT}")
    logger.info("Using Flux Pattern: STT → OpenAI → TTS")
    logger.info("Architecture: Flux (Deepgram) + GPT-4o (OpenAI) + Aura TTS (Deepgram)")
    
    async with websockets.serve(handle_client, "localhost", PORT, max_size=None):
        logger.info(f"✓ Server listening on ws://localhost:{PORT}")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        import traceback
        traceback.print_exc()
