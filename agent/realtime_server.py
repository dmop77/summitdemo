"""
Realtime WebSocket Server for Voice Agent
=========================================
Handles WebSocket connections and integrates with OpenAI Realtime API.
"""

import asyncio
import json
import logging
import os
import base64
import websockets
from datetime import datetime
from typing import Dict, Set, Optional
from dotenv import load_dotenv
from openai import AsyncOpenAI
from voice_agent import TaskCreationVoiceAgent

# Load environment variables
load_dotenv(".env")

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "8081"))

class RealtimeWebSocketServer:
    """WebSocket server that handles real-time communication with the web interface."""
    
    def __init__(self):
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.agent = TaskCreationVoiceAgent()
        self.sessions: Dict[str, dict] = {}  # Store session info per client
        
    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new client connection."""
        self.clients.add(websocket)
        client_id = f"client_{len(self.clients)}"
        self.sessions[client_id] = {
            "websocket": websocket,
            "realtime_session": None,
            "is_connected": False
        }
        logger.info(f"Client {client_id} connected. Total clients: {len(self.clients)}")
        return client_id
    
    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol, client_id: str):
        """Unregister a client connection."""
        self.clients.discard(websocket)
        if client_id in self.sessions:
            session_info = self.sessions[client_id]
            if session_info["realtime_session"]:
                try:
                    await self.agent.client.beta.realtime.sessions.delete(session_info["realtime_session"].id)
                except Exception as e:
                    logger.error(f"Error deleting Realtime session: {e}")
            del self.sessions[client_id]
        logger.info(f"Client {client_id} disconnected. Total clients: {len(self.clients)}")
    
    async def handle_message(self, websocket: websockets.WebSocketServerProtocol, message: str, client_id: str):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "connect":
                await self.handle_connect(websocket, client_id)
            elif message_type == "audio":
                await self.handle_audio(websocket, data, client_id)
            elif message_type == "disconnect":
                await self.handle_disconnect(websocket, client_id)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def handle_connect(self, websocket: websockets.WebSocketServerProtocol, client_id: str):
        """Handle client connection request."""
        try:
            # Create a new Realtime API session
            session = await self.agent.start_session()
            self.sessions[client_id]["realtime_session"] = session
            self.sessions[client_id]["is_connected"] = True
            
            # Send connection confirmation
            await websocket.send(json.dumps({
                "type": "connected",
                "session_id": session.id,
                "message": "Connected to voice agent"
            }))
            
            logger.info(f"Client {client_id} connected to Realtime session: {session.id}")
            
        except Exception as e:
            logger.error(f"Error connecting client {client_id}: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Failed to connect: {str(e)}"
            }))
    
    async def handle_audio(self, websocket: websockets.WebSocketServerProtocol, data: dict, client_id: str):
        """Handle incoming audio data."""
        session_info = self.sessions.get(client_id)
        if not session_info or not session_info["is_connected"]:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Not connected to voice agent"
            }))
            return
        
        try:
            # Decode base64 audio data
            audio_data = base64.b64decode(data.get("audio", ""))
            
            # Send audio to Realtime API
            # Note: This is a simplified implementation
            # In a real implementation, you would stream the audio to the Realtime API
            # and handle the responses asynchronously
            
            # For now, we'll simulate a response
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Send acknowledgment
            await websocket.send(json.dumps({
                "type": "audio_received",
                "message": "Audio received and processed"
            }))
            
        except Exception as e:
            logger.error(f"Error processing audio for client {client_id}: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Error processing audio: {str(e)}"
            }))
    
    async def handle_disconnect(self, websocket: websockets.WebSocketServerProtocol, client_id: str):
        """Handle client disconnect request."""
        await self.unregister_client(websocket, client_id)
        await websocket.send(json.dumps({
            "type": "disconnected",
            "message": "Disconnected from voice agent"
        }))
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle a client WebSocket connection."""
        client_id = await self.register_client(websocket)
        
        try:
            async for message in websocket:
                await self.handle_message(websocket, message, client_id)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} connection closed")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            await self.unregister_client(websocket, client_id)
    
    async def start_server(self):
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server on port {WEBSOCKET_PORT}")
        
        async with websockets.serve(self.handle_client, "localhost", WEBSOCKET_PORT):
            logger.info(f"WebSocket server running on ws://localhost:{WEBSOCKET_PORT}")
            await asyncio.Future()  # Run forever


async def main():
    """Main entry point for the WebSocket server."""
    
    # Validate configuration
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY must be set in environment")
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
