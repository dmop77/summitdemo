"""
Realtime WebSocket Server for Voice Agent
=========================================
Proxies WebSocket connections between browser and OpenAI Realtime API.
"""

import asyncio
import json
import logging
import os
import websockets
from typing import Dict, Set
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

# Agent instructions
AGENT_INSTRUCTIONS = """You are a professional task management assistant for Pulpoo, helping users create tasks efficiently through voice conversation.

YOUR ROLE:
- Capture task information through natural, friendly conversation
- Ask clarifying questions when details are unclear or missing
- Confirm all details before creating the task in Pulpoo
- Be concise but thorough - don't over-explain

TASK INFORMATION TO COLLECT:

REQUIRED:
- Title: A clear, descriptive task title (REQUIRED)

OPTIONAL (Ask if relevant to the task):
- Description: Additional details about the task
- Deadline: When it needs to be completed (get specific date and time)
- Importance: How urgent is it (LOW, MEDIUM, or HIGH) - defaults to HIGH

IMPORTANT NOTES:
- All tasks are automatically assigned to cuevas@pulpoo.com (no need to ask for assignment)
- If no deadline is provided, tasks are set to 24 hours from now
- Importance defaults to HIGH for Pulpoo tasks

CONVERSATION FLOW:
1. Listen to what the user wants to create
2. Extract the core task title first
3. Ask follow-up questions for important missing details
4. Confirm all details before creating
5. Call create_task function with collected information
6. Inform user of success or any errors

Keep responses natural and conversational. Be professional but approachable."""

class RealtimeWebSocketServer:
    """WebSocket server that proxies between browser and OpenAI Realtime API."""
    
    def __init__(self):
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        
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
        """Forward messages from client to OpenAI."""
        try:
            async for message in client_ws:
                try:
                    data = json.loads(message)
                    
                    # Forward to OpenAI
                    await openai_ws.send(message)
                    logger.debug(f"Client -> OpenAI: {data.get('type', 'unknown')}")
                    
                except json.JSONDecodeError:
                    logger.error("Invalid JSON from client")
                except Exception as e:
                    logger.error(f"Error forwarding to OpenAI: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client connection closed")
    
    async def proxy_openai_to_client(self, openai_ws, client_ws):
        """Forward messages from OpenAI to client."""
        try:
            async for message in openai_ws:
                try:
                    data = json.loads(message)
                    
                    # Handle function calls
                    if data.get("type") == "response.function_call_arguments.done":
                        await self.handle_function_call(data, openai_ws)
                    
                    # Forward to client
                    await client_ws.send(message)
                    logger.debug(f"OpenAI -> Client: {data.get('type', 'unknown')}")
                    
                except json.JSONDecodeError:
                    logger.error("Invalid JSON from OpenAI")
                except Exception as e:
                    logger.error(f"Error forwarding to client: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("OpenAI connection closed")
    
    async def handle_function_call(self, data, openai_ws):
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
            "assigned_to_email": "cuevas@pulpoo.com",
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
                    "silence_duration_ms": 500
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
        client_id = f"client_{id(client_ws)}"
        self.clients.add(client_ws)
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
            self.clients.discard(client_ws)
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