"""
Realtime WebSocket Server for Voice Agent
=========================================
Proxies WebSocket connections between browser and OpenAI Realtime API.
"""

import asyncio
import json
import logging
import os
import time
import websockets
from typing import Dict, Set, Optional
from collections import deque
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "8081"))
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

# Rate limiting configuration
AUDIO_SEND_INTERVAL = 1.0  # Minimum seconds between audio chunk sends
MAX_AUDIO_BATCH_SIZE = 5  # Maximum audio chunks to batch together
RETRY_DELAY_429 = 3.0  # Seconds to wait before retrying on 429 error
MAX_RETRIES = 3  # Maximum number of retries for 429 errors

# Agent instructions
AGENT_INSTRUCTIONS = """You are a professional task management assistant for Pulpoo, helping users create tasks efficiently through voice conversation.

YOUR ROLE:
- Capture task information through natural, friendly conversation
- Ask clarifying questions when details are unclear or missing
- Confirm all details before creating the task in Pulpoo
- Be concise but thorough - don't over-explain
- Create meeting notes when requested to summarize conversations

TASK INFORMATION TO COLLECT:

REQUIRED:
- Title: A clear, descriptive task title (REQUIRED)

OPTIONAL (Ask if relevant to the task):
- Description: Additional details about the task
- Deadline: When it needs to be completed (get specific date and time)
- Importance: How urgent is it (LOW, MEDIUM, or HIGH) - defaults to HIGH

MEETING NOTES:
When users request meeting notes or conversation summary, use the create_meeting_notes function with:
- Summary: Key points discussed in the conversation
- Problems: Any device or technical issues mentioned
- Name: User's name if provided

IMPORTANT NOTES:
- All tasks are automatically assigned to cuevas@pulpoo.com, efernandez@pulpoo.com, and perezmd324@gmail.com
- If no deadline is provided, tasks are set to 24 hours from now
- Importance defaults to HIGH for Pulpoo tasks

CONVERSATION FLOW:
1. Listen to what the user wants to create
2. Extract the core task title first
3. Ask follow-up questions for important missing details
4. Confirm all details before creating
5. Call create_task function with collected information
6. Inform user of success or any errors
7. If user requests meeting notes, summarize the conversation and create meeting notes

Keep responses natural and conversational. Be professional but approachable."""

class RealtimeWebSocketServer:
    """WebSocket server that proxies between browser and OpenAI Realtime API."""
    
    def __init__(self):
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.conversation_history: Dict[str, list] = {}  # Track conversations per client
        self.session_start_times: Dict[str, float] = {}  # Track session start times
        
        # Rate limiting and throttling
        self.last_audio_send_time: Dict[str, float] = {}  # Track last audio send time per client
        self.audio_buffer: Dict[str, deque] = {}  # Buffer for batching audio chunks
        self.pending_transcriptions: Dict[str, int] = {}  # Track pending transcriptions per client
        self.rate_limit_stats: Dict[str, dict] = {}  # Track rate limit statistics
        
    async def connect_to_openai(self):
        """Connect to OpenAI Realtime API."""
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        try:
            websocket = await websockets.connect(
                OPENAI_REALTIME_URL,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=20
            )
            logger.info("Connected to OpenAI Realtime API")
            return websocket
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {e}")
            raise
    
    async def proxy_client_to_openai(self, client_ws, openai_ws):
        """Forward messages from client to OpenAI with throttling and batching."""
        client_id = f"client_{id(client_ws)}"
        
        # Initialize buffers and tracking for this client
        if client_id not in self.audio_buffer:
            self.audio_buffer[client_id] = deque(maxlen=MAX_AUDIO_BATCH_SIZE)
        if client_id not in self.last_audio_send_time:
            self.last_audio_send_time[client_id] = 0
        if client_id not in self.rate_limit_stats:
            self.rate_limit_stats[client_id] = {
                "total_sends": 0,
                "throttled_sends": 0,
                "batched_sends": 0,
                "errors_429": 0
            }
        
        try:
            async for message in client_ws:
                try:
                    data = json.loads(message)
                    message_type = data.get('type', 'unknown')
                    
                    # Handle audio messages with throttling and batching
                    if message_type == "input_audio_buffer.append":
                        await self._handle_audio_message(client_id, message, openai_ws)
                    else:
                        # Forward non-audio messages immediately
                        await self._send_with_retry(openai_ws, message, client_id)
                        logger.debug(f"Client -> OpenAI: {message_type}")
                    
                except json.JSONDecodeError:
                    logger.error("Invalid JSON from client")
                except Exception as e:
                    logger.error(f"Error forwarding to OpenAI: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} connection closed")
    
    async def _handle_audio_message(self, client_id: str, message: str, openai_ws):
        """Handle audio messages with throttling and batching."""
        current_time = time.time()
        time_since_last_send = current_time - self.last_audio_send_time[client_id]
        
        # Add to buffer
        self.audio_buffer[client_id].append(message)
        
        # Check if we should send based on throttling interval or buffer full
        should_send = (
            time_since_last_send >= AUDIO_SEND_INTERVAL or
            len(self.audio_buffer[client_id]) >= MAX_AUDIO_BATCH_SIZE
        )
        
        # Check if we have pending transcriptions (close the loop)
        if client_id in self.pending_transcriptions and self.pending_transcriptions[client_id] > 0:
            logger.debug(f"Delaying audio send - {self.pending_transcriptions[client_id]} pending transcriptions")
            should_send = False
        
        if should_send and self.audio_buffer[client_id]:
            # Send all buffered audio chunks
            stats = self.rate_limit_stats[client_id]
            
            if len(self.audio_buffer[client_id]) > 1:
                stats["batched_sends"] += 1
                logger.debug(f"Sending batch of {len(self.audio_buffer[client_id])} audio chunks")
            
            for audio_msg in self.audio_buffer[client_id]:
                await self._send_with_retry(openai_ws, audio_msg, client_id)
                stats["total_sends"] += 1
            
            self.audio_buffer[client_id].clear()
            self.last_audio_send_time[client_id] = current_time
        else:
            if not should_send:
                self.rate_limit_stats[client_id]["throttled_sends"] += 1
    
    async def _send_with_retry(self, openai_ws, message: str, client_id: str = None, retries: int = 0):
        """Send message to OpenAI with retry logic for 429 errors."""
        try:
            await openai_ws.send(message)
        except Exception as e:
            error_str = str(e)
            
            # Check for 429 rate limit error
            if "429" in error_str or "rate limit" in error_str.lower():
                if client_id:
                    self.rate_limit_stats[client_id]["errors_429"] += 1
                
                if retries < MAX_RETRIES:
                    logger.warning(f"Rate limit hit (429), waiting {RETRY_DELAY_429}s before retry {retries + 1}/{MAX_RETRIES}")
                    await asyncio.sleep(RETRY_DELAY_429)
                    await self._send_with_retry(openai_ws, message, client_id, retries + 1)
                else:
                    logger.error(f"Max retries reached for 429 error. Message dropped.")
                    raise
            else:
                logger.error(f"Error sending to OpenAI: {e}")
                raise
    
    async def proxy_openai_to_client(self, openai_ws, client_ws):
        """Forward messages from OpenAI to client and track transcriptions."""
        client_id = f"client_{id(client_ws)}"
        
        # Initialize pending transcriptions counter
        if client_id not in self.pending_transcriptions:
            self.pending_transcriptions[client_id] = 0
        
        try:
            async for message in openai_ws:
                try:
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    
                    # Track transcription lifecycle (close the loop)
                    if message_type == "input_audio_buffer.speech_started":
                        # Increment pending transcriptions when speech is detected
                        self.pending_transcriptions[client_id] += 1
                        logger.debug(f"Speech started - pending transcriptions: {self.pending_transcriptions[client_id]}")
                    
                    elif message_type in ["conversation.item.input_audio_transcription.completed",
                                         "conversation.item.input_audio_transcription.failed"]:
                        # Decrement when transcription completes or fails
                        if self.pending_transcriptions[client_id] > 0:
                            self.pending_transcriptions[client_id] -= 1
                        logger.debug(f"Transcription completed - pending: {self.pending_transcriptions[client_id]}")
                    
                    # Track conversation history
                    if message_type in ["conversation.item.input_audio_transcription.completed", 
                                       "response.text.done"]:
                        if client_id not in self.conversation_history:
                            self.conversation_history[client_id] = []
                        
                        if message_type == "conversation.item.input_audio_transcription.completed":
                            self.conversation_history[client_id].append({
                                "type": "user",
                                "content": data.get("transcript", ""),
                                "timestamp": data.get("created_at", "")
                            })
                        elif message_type == "response.text.done":
                            self.conversation_history[client_id].append({
                                "type": "assistant", 
                                "content": data.get("text", ""),
                                "timestamp": data.get("created_at", "")
                            })
                    
                    # Handle function calls
                    if message_type == "response.function_call_arguments.done":
                        await self.handle_function_call(data, openai_ws, client_id)
                    
                    # Check for rate limit errors from OpenAI
                    if message_type == "error" and data.get("error", {}).get("code") == "rate_limit_exceeded":
                        logger.error(f"Rate limit error from OpenAI: {data.get('error', {}).get('message', 'Unknown')}")
                        if client_id in self.rate_limit_stats:
                            self.rate_limit_stats[client_id]["errors_429"] += 1
                    
                    # Forward to client
                    await client_ws.send(message)
                    logger.debug(f"OpenAI -> Client: {message_type}")
                    
                except json.JSONDecodeError:
                    logger.error("Invalid JSON from OpenAI")
                except Exception as e:
                    logger.error(f"Error forwarding to client: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"OpenAI connection closed for {client_id}")
    
    async def handle_function_call(self, data, openai_ws, client_id=None):
        """Handle function calls from the agent."""
        try:
            call_id = data.get("call_id")
            name = data.get("name")
            arguments = json.loads(data.get("arguments", "{}"))
            
            logger.info(f"Function call: {name} with args: {arguments}")
            
            # Handle create_task function
            if name == "create_task":
                result = await self.create_task(
                    title=arguments.get("title"),
                    description=arguments.get("description"),
                    deadline=arguments.get("deadline"),
                    importance=arguments.get("importance", "HIGH")
                )
            elif name == "create_meeting_notes":
                result = await self.create_meeting_notes(
                    summary=arguments.get("summary"),
                    problems=arguments.get("problems"),
                    name=arguments.get("name"),
                    client_id=client_id
                )
            elif name == "get_current_date_time":
                from datetime import datetime
                result = f"The current date and time is {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
            else:
                result = f"Unknown function: {name}"
            
            # Send function result back to OpenAI
            response = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": result
                }
            }
            
            await openai_ws.send(json.dumps(response))
            
            # Trigger response generation
            await openai_ws.send(json.dumps({"type": "response.create"}))
            
        except Exception as e:
            logger.error(f"Error handling function call: {e}")
    
    async def create_task(self, title: str, description: str = None, 
                         deadline: str = None, importance: str = "HIGH"):
        """Create a task in Pulpoo."""
        import aiohttp
        from datetime import datetime, timedelta
        import pytz
        
        # Validate importance
        if importance.upper() not in ["LOW", "MEDIUM", "HIGH"]:
            importance = "HIGH"
        else:
            importance = importance.upper()
        
        # Default deadline if not provided
        if not deadline:
            deadline_dt = datetime.now(pytz.UTC) + timedelta(hours=24)
            deadline = deadline_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Build payload
        payload = {
            "title": title,
            "description": description or f"Task created via voice agent: {title}",
            "assigned_to_email": ["cuevas@pulpoo.com", "efernandez@pulpoo.com", "perezmd324@gmail.com"],
            "deadline": deadline,
            "importance": importance,
        }
        
        logger.info(f"Creating task in Pulpoo: {payload}")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "X-API-Key": os.getenv("PULPOO_API_KEY"),
                    "Content-Type": "application/json",
                }
                
                async with session.post(
                    "https://api.pulpoo.com/v1/external/tasks/create",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_data = await response.json()
                    
                    if response.status in [200, 201]:
                        result = f"Task created successfully in Pulpoo! "
                        result += f"Title: {title}. "
                        result += f"Assigned to: cuevas@pulpoo.com. "
                        if deadline:
                            result += f"Deadline: {deadline}. "
                        result += f"Importance: {importance}."
                        
                        logger.info(f"Task created successfully: {title}")
                        return result
                    else:
                        error_msg = response_data.get("error", "Unknown error")
                        logger.error(f"Pulpoo API error {response.status}: {error_msg}")
                        return f"I encountered an error creating the task: {error_msg}. Would you like to try again?"
                        
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return f"I'm having trouble connecting to Pulpoo. Please check your connection and try again."
    
    async def create_meeting_notes(self, summary: str, problems: str = None, 
                                 name: str = None, client_id: str = None):
        """Create meeting notes with conversation summary."""
        import aiohttp
        from datetime import datetime
        import time
        
        # Calculate time elapsed
        time_elapsed = "Unknown"
        if client_id and client_id in self.session_start_times:
            elapsed_seconds = time.time() - self.session_start_times[client_id]
            hours = int(elapsed_seconds // 3600)
            minutes = int((elapsed_seconds % 3600) // 60)
            time_elapsed = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        
        # Get current date and time
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M")
        
        # Build meeting notes content
        meeting_notes_content = f"""MEETING NOTES
================

Summary:
{summary}

Problems with device:
{problems or "None reported"}

Name: {name or "Not specified"}

Date: {current_date}
Time: {current_time}
Time elapsed: {time_elapsed}

---
Generated by Pulpoo Voice Assistant
"""
        
        # Create task with meeting notes
        task_title = f"Meeting Notes - {current_date}"
        task_description = meeting_notes_content
        
        # Use the existing create_task function
        return await self.create_task(
            title=task_title,
            description=task_description,
            importance="MEDIUM"
        )
    
    def log_rate_limit_stats(self, client_id: str):
        """Log rate limiting statistics for a client session."""
        if client_id in self.rate_limit_stats:
            stats = self.rate_limit_stats[client_id]
            logger.info(f"\n{'='*50}")
            logger.info(f"Rate Limit Statistics for {client_id}")
            logger.info(f"{'='*50}")
            logger.info(f"Total audio sends: {stats['total_sends']}")
            logger.info(f"Throttled sends: {stats['throttled_sends']}")
            logger.info(f"Batched sends: {stats['batched_sends']}")
            logger.info(f"429 Errors: {stats['errors_429']}")
            logger.info(f"{'='*50}\n")
    
    async def initialize_session(self, openai_ws):
        """Initialize the OpenAI Realtime session with configuration."""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": AGENT_INSTRUCTIONS,
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 1200  # Increased from 500 to reduce back-to-back transcriptions
                },
                "tools": [
                    {
                        "type": "function",
                        "name": "create_task",
                        "description": "Create a new task in Pulpoo via the API",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "Task title (required)"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Detailed description of the task"
                                },
                                "deadline": {
                                    "type": "string",
                                    "description": "Deadline in ISO 8601 format (e.g., '2025-01-15T17:00:00Z')"
                                },
                                "importance": {
                                    "type": "string",
                                    "enum": ["LOW", "MEDIUM", "HIGH"],
                                    "description": "Task importance - defaults to HIGH"
                                }
                            },
                            "required": ["title"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "get_current_date_time",
                        "description": "Get the current date and time for deadline calculations",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "type": "function",
                        "name": "create_meeting_notes",
                        "description": "Create meeting notes summarizing the conversation with structured format",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "summary": {
                                    "type": "string",
                                    "description": "Summary of key points discussed in the conversation"
                                },
                                "problems": {
                                    "type": "string",
                                    "description": "Any device or technical problems mentioned during the conversation"
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Name of the person in the meeting/conversation"
                                }
                            },
                            "required": ["summary"]
                        }
                    }
                ],
                "tool_choice": "auto",
                "temperature": 0.8
            }
        }
        
        await openai_ws.send(json.dumps(config))
        logger.info("Session initialized with configuration")
    
    async def handle_client(self, client_ws, path):
        """Handle a client WebSocket connection."""
        import time
        
        client_id = f"client_{id(client_ws)}"
        self.clients.add(client_ws)
        self.session_start_times[client_id] = time.time()  # Track session start time
        logger.info(f"Client {client_id} connected from {client_ws.remote_address}")
        
        openai_ws = None
        
        try:
            # Connect to OpenAI Realtime API
            openai_ws = await self.connect_to_openai()
            
            # Initialize session
            await self.initialize_session(openai_ws)
            
            # Send connection confirmation to client
            await client_ws.send(json.dumps({
                "type": "session.connected",
                "message": "Connected to OpenAI Realtime API"
            }))
            
            # Create bidirectional proxy
            await asyncio.gather(
                self.proxy_client_to_openai(client_ws, openai_ws),
                self.proxy_openai_to_client(openai_ws, client_ws),
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            try:
                await client_ws.send(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
            except:
                pass
        finally:
            # Log rate limiting statistics before cleanup
            self.log_rate_limit_stats(client_id)
            
            self.clients.discard(client_ws)
            
            # Clean up session data
            if client_id in self.session_start_times:
                del self.session_start_times[client_id]
            if client_id in self.conversation_history:
                del self.conversation_history[client_id]
            
            # Clean up rate limiting data
            if client_id in self.last_audio_send_time:
                del self.last_audio_send_time[client_id]
            if client_id in self.audio_buffer:
                del self.audio_buffer[client_id]
            if client_id in self.pending_transcriptions:
                del self.pending_transcriptions[client_id]
            if client_id in self.rate_limit_stats:
                del self.rate_limit_stats[client_id]
            
            if openai_ws:
                await openai_ws.close()
            logger.info(f"Client {client_id} disconnected. Remaining clients: {len(self.clients)}")
    
    async def start_server(self):
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server on port {WEBSOCKET_PORT}")
        
        async with websockets.serve(
            self.handle_client, 
            "localhost", 
            WEBSOCKET_PORT,
            ping_interval=20,
            ping_timeout=20
        ):
            logger.info(f"WebSocket server running on ws://localhost:{WEBSOCKET_PORT}")
            logger.info("Waiting for client connections...")
            await asyncio.Future()  # Run forever


async def main():
    """Main entry point for the WebSocket server."""
    
    # Validate configuration
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not found in environment")
        return
    
    server = RealtimeWebSocketServer()
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("Shutting down WebSocket server...")
    except Exception as e:
        logger.error(f"Error running WebSocket server: {e}")


if __name__ == "__main__":
    asyncio.run(main())