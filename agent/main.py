"""
Main server for the Voice Agent.

Provides:
- HTTP endpoint to serve the web UI
- WebSocket endpoint for real-time audio/text communication
- Integration with Deepgram for speech-to-text
- Integration with Pydantic AI agent
"""

import asyncio
import json
import logging
import os
import base64
from typing import Optional

import aiohttp
from aiohttp import web
import deepgram

from config import get_voice_config
from voice_agent import VoiceAssistant

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VoiceServer:
    """WebSocket server for voice interactions."""

    def __init__(self):
        """Initialize the voice server."""
        self.config = get_voice_config()
        self.voice_assistant = VoiceAssistant()
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP and WebSocket routes."""
        self.app.router.add_get("/", self._http_handler)
        self.app.router.add_get("/ws", self._websocket_handler)
        # Serve static files (pulpoo.png, etc.)
        static_path = os.path.join(os.path.dirname(__file__), "..", "server")
        if os.path.exists(static_path):
            self.app.router.add_static("/static", static_path)

    async def _http_handler(self, request: web.Request) -> web.Response:
        """Serve the HTML UI."""
        html_path = os.path.join(
            os.path.dirname(__file__), "..", "server", "index.html"
        )
        if os.path.exists(html_path):
            with open(html_path, "r") as f:
                return web.Response(text=f.read(), content_type="text/html")
        return web.Response(
            text="<h1>Voice Agent Ready</h1><p>WebSocket: ws://localhost:8084/ws</p>",
            content_type="text/html",
        )

    async def _websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections for voice streaming."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        session_id = f"session_{id(ws)}"
        logger.info(f"New WebSocket connection: {session_id}")

        deepgram_ws: Optional[object] = None
        current_transcript = ""

        try:
            # Initialize voice assistant
            await self.voice_assistant.initialize()

            # Connect to Deepgram for STT
            dg_client = deepgram.Deepgram(self.config.deepgram_api_key)

            # Create Deepgram websocket options
            options = deepgram.PrerecordedOptions(
                model=self.config.deepgram_model,
                language="en",
                punctuate=True,
            )

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
                                response = await dg_client.transcription.prerecorded(
                                    audio_bytes,
                                    options,
                                )

                                # Extract transcript
                                if response and response.get("results"):
                                    transcript = response["results"].get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")

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
    logger.info("Using: Deepgram STT + OpenAI LLM + OpenAI TTS")

    server = VoiceServer()
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
