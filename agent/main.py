"""
Main server for the Voice Agent.

Provides:
- HTTP endpoints for UI pages and setup
- WebSocket endpoint for real-time audio/text communication
- Integration with Deepgram for speech-to-text
- Integration with Pydantic AI agent for intelligent responses
"""

import asyncio
import json
import logging
import os
import base64
import uuid
from typing import Optional

from dotenv import load_dotenv
import aiohttp
from aiohttp import web
from deepgram import DeepgramClient

# Load environment variables from .env file
load_dotenv()

from config import get_voice_config
from voice_agent import VoiceAssistant
from web_scraper import WebScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VoiceServer:
    """Web server for voice interactions with multi-page support."""

    def __init__(self):
        """Initialize the voice server."""
        self.config = get_voice_config()
        self.voice_assistant = VoiceAssistant()
        self.web_scraper = WebScraper(self.config.openai_api_key)
        self.app = web.Application()
        self.sessions = {}  # Store session data
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP and WebSocket routes."""
        self.app.router.add_get("/", self._index_handler)
        self.app.router.add_get("/input.html", self._input_handler)
        self.app.router.add_get("/chat.html", self._chat_handler)
        self.app.router.add_post("/setup", self._setup_handler)
        self.app.router.add_get("/ws", self._websocket_handler)
        
        # Serve static files
        static_path = os.path.join(os.path.dirname(__file__), "..", "server")
        if os.path.exists(static_path):
            self.app.router.add_static("/static", static_path)
            self.app.router.add_static("/", static_path)

    async def _index_handler(self, request: web.Request) -> web.Response:
        """Serve the main index page."""
        html_path = os.path.join(
            os.path.dirname(__file__), "..", "server", "index.html"
        )
        if os.path.exists(html_path):
            with open(html_path, "r") as f:
                return web.Response(text=f.read(), content_type="text/html")
        return web.Response(
            text="<h1>Voice Agent Ready</h1><p>Please navigate to http://localhost:8084</p>",
            content_type="text/html",
        )

    async def _input_handler(self, request: web.Request) -> web.Response:
        """Serve the user input form page."""
        html_path = os.path.join(
            os.path.dirname(__file__), "..", "server", "input.html"
        )
        if os.path.exists(html_path):
            with open(html_path, "r") as f:
                return web.Response(text=f.read(), content_type="text/html")
        return web.Response(text="Input form not found", status=404)

    async def _chat_handler(self, request: web.Request) -> web.Response:
        """Serve the voice chat page."""
        html_path = os.path.join(
            os.path.dirname(__file__), "..", "server", "chat.html"
        )
        if os.path.exists(html_path):
            with open(html_path, "r") as f:
                return web.Response(text=f.read(), content_type="text/html")
        return web.Response(text="Chat page not found", status=404)

    async def _setup_handler(self, request: web.Request) -> web.Response:
        """Handle user setup and web scraping initiation."""
        try:
            data = await request.json()
            
            name = data.get("name", "").strip()
            email = data.get("email", "").strip()
            website_url = data.get("website_url", "").strip()
            
            if not all([name, email, website_url]):
                return web.json_response(
                    {"error": "Missing required fields"},
                    status=400
                )
            
            # Create session
            session_id = str(uuid.uuid4())
            
            logger.info(f"Setup request: {name} ({email}) - {website_url}")
            
            # Scrape the website asynchronously
            try:
                scraped_result = await self.web_scraper.scrape_and_embed(website_url)
                if not scraped_result:
                    logger.warning(f"Failed to scrape {website_url}")
                    scraped_content = None
                else:
                    scraped_content, embedding = scraped_result
            except Exception as e:
                logger.error(f"Error scraping website: {e}")
                scraped_content = None
            
            # Store session data
            self.sessions[session_id] = {
                "name": name,
                "email": email,
                "website_url": website_url,
                "scraped_content": scraped_content,
            }
            
            # Initialize voice assistant with user context
            self.voice_assistant.update_context_with_user_info(name, email, website_url)
            # Set scraped content if available
            if scraped_content and self.voice_assistant.conversation_context:
                # Update context with scraped content
                self.voice_assistant.conversation_context = self.voice_assistant.conversation_context.model_copy(
                    update={"scraped_content": scraped_content}
                )
            
            logger.info(f"Session created: {session_id}")
            
            return web.json_response({
                "success": True,
                "session_id": session_id,
                "message": "Ready for voice chat",
                "scraped_content": {
                    "title": scraped_content.title if scraped_content else None,
                    "summary": scraped_content.summary if scraped_content else None,
                } if scraped_content else None,
            })
            
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON"},
                status=400
            )
        except Exception as e:
            logger.error(f"Error in setup handler: {e}", exc_info=True)
            return web.json_response(
                {"error": f"Server error: {str(e)}"},
                status=500
            )

    async def _websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections for voice streaming."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        session_id = f"session_{id(ws)}"
        logger.info(f"New WebSocket connection: {session_id}")

        current_transcript = ""

        try:
            # Initialize voice assistant
            await self.voice_assistant.initialize()

            # Connect to Deepgram for STT
            dg_client = DeepgramClient(api_key=self.config.deepgram_api_key)

            # Listen for messages from browser
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    # Handle audio data
                    if data.get("type") == "input_audio_buffer.append":
                        audio_b64 = data.get("audio", "")
                        if audio_b64:
                            audio_bytes = base64.b64decode(audio_b64)

                            # Send to Deepgram for transcription
                            try:
                                response = await dg_client.listen.v1.media.transcribe_file(
                                    request=audio_bytes,
                                    model=self.config.deepgram_model,
                                    language="en",
                                    punctuate=True,
                                )

                                # Extract transcript from Deepgram response
                                transcript = ""
                                if response and response.results:
                                    channels = response.results.channels
                                    if channels and len(channels) > 0:
                                        alternatives = channels[0].alternatives
                                        if alternatives and len(alternatives) > 0:
                                            transcript = alternatives[0].transcript or ""

                                    if transcript and transcript != current_transcript:
                                        current_transcript = transcript
                                        logger.info(f"Transcript: {transcript}")

                                        # Send transcript to client
                                        await ws.send_json({
                                            "type": "user.transcript",
                                            "text": transcript,
                                        })

                                        # Get agent response
                                        response_text = await self.voice_assistant.process_message(
                                            transcript, session_id
                                        )

                                        # Send agent response
                                        await ws.send_json({
                                            "type": "response.text",
                                            "text": response_text,
                                        })

                                        # Synthesize speech with OpenAI
                                        audio_data = await self._synthesize_speech(response_text)
                                        if audio_data:
                                            await ws.send_json({
                                                "type": "response.audio.delta",
                                                "delta": audio_data,
                                            })

                            except Exception as e:
                                logger.error(f"Error transcribing audio: {e}")
                                await ws.send_json({
                                    "type": "error",
                                    "message": f"Transcription error: {str(e)}",
                                })

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")

        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
        finally:
            await self.voice_assistant.cleanup()
            logger.info(f"WebSocket connection closed: {session_id}")

        return ws

    async def _synthesize_speech(self, text: str) -> Optional[str]:
        """
        Synthesize speech using OpenAI TTS.

        Args:
            text: Text to synthesize

        Returns:
            Base64-encoded audio data or None on error
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.config.openai_api_key}",
                }

                payload = {
                    "model": "tts-1",
                    "input": text,
                    "voice": self.config.openai_tts_voice,
                }

                async with session.post(
                    "https://api.openai.com/v1/audio/speech",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        audio_bytes = await response.read()
                        return base64.b64encode(audio_bytes).decode()
                    else:
                        logger.error(f"TTS error: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            return None

    async def start(self):
        """Start the server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.config.host, self.config.port)
        await site.start()

        logger.info(f"✓ Server listening on http://{self.config.host}:{self.config.port}")
        logger.info(f"✓ Open http://localhost:{self.config.port} in your browser")
        logger.info("Ready to accept connections!")

        # Keep server running
        try:
            await asyncio.Future()
        except KeyboardInterrupt:
            pass
        finally:
            await runner.cleanup()


async def main():
    """Main entry point."""
    logger.info("Starting Voice Agent Server")
    logger.info("Using: Deepgram STT + OpenAI LLM + OpenAI TTS + Web Scraping")

    server = VoiceServer()
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
