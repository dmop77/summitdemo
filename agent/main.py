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
import struct
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

    @staticmethod
    def _create_wav_header(audio_bytes: bytes, sample_rate: int = 24000, channels: int = 1,
                          sample_width: int = 2) -> bytes:
        """
        Create WAV file header for PCM16 audio data.

        Args:
            audio_bytes: Raw PCM16 audio data
            sample_rate: Sample rate in Hz (default 24000)
            channels: Number of channels (default 1 for mono)
            sample_width: Bytes per sample (default 2 for PCM16)

        Returns:
            Complete WAV file with headers
        """
        # Calculate sizes
        byte_rate = sample_rate * channels * sample_width
        block_align = channels * sample_width

        # WAV header structure
        wav_header = b'RIFF'
        file_size = 36 + len(audio_bytes)
        wav_header += struct.pack('<I', file_size)
        wav_header += b'WAVE'

        # fmt sub-chunk
        wav_header += b'fmt '
        wav_header += struct.pack('<I', 16)  # Subchunk size
        wav_header += struct.pack('<H', 1)   # Audio format (1 = PCM)
        wav_header += struct.pack('<H', channels)
        wav_header += struct.pack('<I', sample_rate)
        wav_header += struct.pack('<I', byte_rate)
        wav_header += struct.pack('<H', block_align)
        wav_header += struct.pack('<H', sample_width * 8)  # Bits per sample

        # data sub-chunk
        wav_header += b'data'
        wav_header += struct.pack('<I', len(audio_bytes))
        wav_header += audio_bytes

        return wav_header

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
            if scraped_content:
                # Update context and agent prompt with scraped content
                self.voice_assistant.update_context_with_scraped_content(scraped_content)
            else:
                logger.warning(f"No scraped content available for {website_url}")
            
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

    async def _send_greeting(self, user_name: str, ws: web.WebSocketResponse) -> str:
        """
        Send an automatic greeting to the user when voice session starts.

        Args:
            user_name: User's name
            ws: WebSocket connection

        Returns:
            Greeting message text
        """
        try:
            session_id = f"session_{id(ws)}"

            # Use a simple trigger message to get the agent to greet naturally
            # The system prompt already instructs the agent to greet the user by name
            greeting_trigger = "start"

            # Generate greeting from agent (agent will greet based on system prompt)
            greeting_response = await self.voice_assistant.process_message(
                greeting_trigger, session_id
            )

            logger.info(f"Sending greeting: {greeting_response}")

            # Send greeting text to transcript
            await ws.send_json({
                "type": "response.text",
                "text": greeting_response,
            })

            # Synthesize and send greeting audio
            audio_data = await self._synthesize_speech(greeting_response)
            if audio_data:
                await ws.send_json({
                    "type": "response.audio.delta",
                    "delta": audio_data,
                })
                # Send audio completion event
                await ws.send_json({
                    "type": "response.audio.done",
                })
            else:
                logger.warning("Failed to synthesize greeting audio")

            return greeting_response

        except Exception as e:
            logger.error(f"Error sending greeting: {e}", exc_info=True)
            return ""

    async def _websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections for voice streaming."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        session_id = f"session_{id(ws)}"
        logger.info(f"New WebSocket connection: {session_id}")

        greeting_sent = False

        # Audio accumulation for complete utterances
        audio_buffer = []
        silence_chunks = 0
        SILENCE_THRESHOLD = 3  # Number of silent chunks (~1.5 seconds) - balanced for accuracy and latency
        MIN_SPEECH_CHUNKS = 1  # Minimum speech chunks before considering it a valid utterance
        accumulated_transcript = ""
        speech_chunk_count = 0
        is_agent_speaking = False  # Track when agent is responding to avoid processing user audio

        try:
            # Initialize voice assistant
            await self.voice_assistant.initialize()

            # Reset conversation history for this new session
            self.voice_assistant.reset_conversation()

            # Connect to Deepgram for STT
            dg_client = DeepgramClient(api_key=self.config.deepgram_api_key)

            # Send automatic greeting if user info is available (after WebSocket is ready)
            if self.voice_assistant.conversation_context and self.voice_assistant.conversation_context.user_info and not greeting_sent:
                try:
                    await self._send_greeting(
                        self.voice_assistant.conversation_context.user_info.name,
                        ws
                    )
                    greeting_sent = True
                except Exception as e:
                    logger.error(f"Error sending greeting: {e}")

            # Listen for messages from browser
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    # Handle audio data
                    if data.get("type") == "input_audio_buffer.append":
                        audio_b64 = data.get("audio", "")
                        if audio_b64:
                            # Skip processing if agent is currently speaking
                            if is_agent_speaking:
                                logger.debug("Agent is speaking, skipping user audio")
                                continue

                            # Decode base64 to get raw PCM16 bytes
                            raw_audio_bytes = base64.b64decode(audio_b64)

                            # Add to buffer for accumulation
                            audio_buffer.append(raw_audio_bytes)

                            # Wrap raw PCM16 audio in WAV format for Deepgram (for VAD check)
                            wav_audio = self._create_wav_header(
                                raw_audio_bytes,
                                sample_rate=24000,
                                channels=1,
                                sample_width=2
                            )

                            # Send to Deepgram just to check for speech activity (VAD)
                            try:
                                response = dg_client.listen.v1.media.transcribe_file(
                                    request=wav_audio,
                                    model=self.config.deepgram_model,
                                    language="en",
                                    punctuate=True,
                                )

                                # Check if this chunk has speech (just for VAD, don't use transcript)
                                has_speech = False
                                if response and hasattr(response, 'results') and response.results:
                                    channels = response.results.channels
                                    if channels and len(channels) > 0:
                                        alternatives = channels[0].alternatives
                                        if alternatives and len(alternatives) > 0:
                                            transcript = alternatives[0].transcript or ""
                                            confidence = alternatives[0].confidence if hasattr(alternatives[0], 'confidence') else 0.0
                                            if transcript and transcript.strip() and confidence > 0.3:
                                                has_speech = True
                                                logger.debug(f"Speech detected in chunk (confidence: {confidence:.2f})")

                                if has_speech:
                                    # Speech detected
                                    speech_chunk_count += 1
                                    silence_chunks = 0
                                else:
                                    # Silence detected
                                    silence_chunks += 1
                                    logger.debug(f"Silence chunk {silence_chunks}/{SILENCE_THRESHOLD}")

                                # Process when silence threshold reached AND we have enough speech
                                if (silence_chunks >= SILENCE_THRESHOLD and
                                    len(audio_buffer) > MIN_SPEECH_CHUNKS and
                                    speech_chunk_count >= MIN_SPEECH_CHUNKS):

                                    # Concatenate all accumulated audio
                                    complete_audio = b''.join(audio_buffer)

                                    # Create WAV file from complete audio
                                    complete_wav = self._create_wav_header(
                                        complete_audio,
                                        sample_rate=24000,
                                        channels=1,
                                        sample_width=2
                                    )

                                    logger.info(f"Processing complete utterance: {len(complete_audio)} bytes, {speech_chunk_count} speech chunks")

                                    # Send complete audio to Deepgram for transcription
                                    final_response = dg_client.listen.v1.media.transcribe_file(
                                        request=complete_wav,
                                        model=self.config.deepgram_model,
                                        language="en",
                                        punctuate=True,
                                    )

                                    # Extract final transcript
                                    final_transcript = ""
                                    if final_response and hasattr(final_response, 'results') and final_response.results:
                                        channels = final_response.results.channels
                                        if channels and len(channels) > 0:
                                            alternatives = channels[0].alternatives
                                            if alternatives and len(alternatives) > 0:
                                                final_transcript = alternatives[0].transcript or ""

                                    if final_transcript and final_transcript.strip():
                                        logger.info(f"Complete utterance transcribed: {final_transcript}")

                                        # Set agent speaking flag
                                        is_agent_speaking = True

                                        # Send transcript to client
                                        await ws.send_json({
                                            "type": "user.transcript",
                                            "text": final_transcript,
                                        })

                                        # Get agent response
                                        response_text = await self.voice_assistant.process_message(
                                            final_transcript, session_id
                                        )

                                        logger.info(f"Agent will respond: {response_text[:100]}")

                                        # Send agent response
                                        await ws.send_json({
                                            "type": "response.text",
                                            "text": response_text,
                                        })

                                        # Synthesize speech with Cartesia
                                        audio_data = await self._synthesize_speech(response_text)
                                        if audio_data:
                                            logger.info(f"Sending audio response: {len(audio_data)} chars")
                                            await ws.send_json({
                                                "type": "response.audio.delta",
                                                "delta": audio_data,
                                            })
                                            # Send audio completion event
                                            await ws.send_json({
                                                "type": "response.audio.done",
                                            })
                                        else:
                                            logger.warning("Failed to synthesize audio response")

                                    # Reset accumulation
                                    audio_buffer = []
                                    silence_chunks = 0
                                    speech_chunk_count = 0
                                    is_agent_speaking = False

                            except Exception as e:
                                # Check if it's a timeout error (408) - these are common and can be ignored
                                error_msg = str(e)
                                if "408" in error_msg or "timeout" in error_msg.lower():
                                    logger.debug(f"Deepgram timeout (silence): {e}")
                                    # Treat timeout as silence
                                    silence_chunks += 1
                                    logger.debug(f"Timeout = silence chunk {silence_chunks}/{SILENCE_THRESHOLD}")

                                    # Process if we have accumulated audio and reached threshold
                                    if (silence_chunks >= SILENCE_THRESHOLD and
                                        len(audio_buffer) > MIN_SPEECH_CHUNKS and
                                        speech_chunk_count >= MIN_SPEECH_CHUNKS):

                                        # Concatenate all accumulated audio
                                        complete_audio = b''.join(audio_buffer)

                                        # Create WAV file from complete audio
                                        complete_wav = self._create_wav_header(
                                            complete_audio,
                                            sample_rate=24000,
                                            channels=1,
                                            sample_width=2
                                        )

                                        logger.info(f"Processing complete utterance (after timeout): {len(complete_audio)} bytes")

                                        try:
                                            # Send complete audio to Deepgram for transcription
                                            final_response = dg_client.listen.v1.media.transcribe_file(
                                                request=complete_wav,
                                                model=self.config.deepgram_model,
                                                language="en",
                                                punctuate=True,
                                            )

                                            # Extract final transcript
                                            final_transcript = ""
                                            if final_response and hasattr(final_response, 'results') and final_response.results:
                                                channels = final_response.results.channels
                                                if channels and len(channels) > 0:
                                                    alternatives = channels[0].alternatives
                                                    if alternatives and len(alternatives) > 0:
                                                        final_transcript = alternatives[0].transcript or ""

                                            if final_transcript and final_transcript.strip():
                                                logger.info(f"Complete utterance transcribed: {final_transcript}")

                                                is_agent_speaking = True

                                                await ws.send_json({
                                                    "type": "user.transcript",
                                                    "text": final_transcript,
                                                })

                                                response_text = await self.voice_assistant.process_message(
                                                    final_transcript, session_id
                                                )

                                                logger.info(f"Agent will respond: {response_text[:100]}")

                                                await ws.send_json({
                                                    "type": "response.text",
                                                    "text": response_text,
                                                })

                                                audio_data = await self._synthesize_speech(response_text)
                                                if audio_data:
                                                    logger.info(f"Sending audio response: {len(audio_data)} chars")
                                                    await ws.send_json({
                                                        "type": "response.audio.delta",
                                                        "delta": audio_data,
                                                    })
                                                    await ws.send_json({
                                                        "type": "response.audio.done",
                                                    })

                                            # Reset
                                            audio_buffer = []
                                            silence_chunks = 0
                                            speech_chunk_count = 0
                                            is_agent_speaking = False

                                        except Exception as transcribe_error:
                                            logger.error(f"Error transcribing complete audio: {transcribe_error}")
                                            audio_buffer = []
                                            silence_chunks = 0
                                            speech_chunk_count = 0
                                            is_agent_speaking = False

                                else:
                                    logger.error(f"Error in VAD check: {e}")
                                    # Don't reset buffers on non-timeout errors, continue accumulating

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
        Synthesize speech using Cartesia TTS.

        Args:
            text: Text to synthesize

        Returns:
            Base64-encoded audio data or None on error
        """
        try:
            logger.info(f"Synthesizing speech: {text[:100]}...")

            # Check if Cartesia API key is configured
            if not self.config.cartesia_api_key:
                logger.error("Cartesia API key not configured")
                return None

            async with aiohttp.ClientSession() as session:
                headers = {
                    "X-API-Key": self.config.cartesia_api_key,
                    "Content-Type": "application/json",
                    "Cartesia-Version": "2025-04-16",
                }

                payload = {
                    "model_id": "sonic-english",
                    "transcript": text,
                    "voice": {
                        "mode": "id",
                        "id": self.config.cartesia_voice_id,
                    },
                    "output_format": {
                        "container": "raw",
                        "encoding": "pcm_s16le",
                        "sample_rate": 24000,
                    }
                }

                logger.info(f"Calling Cartesia TTS API with voice ID: {self.config.cartesia_voice_id}")

                async with session.post(
                    "https://api.cartesia.ai/tts/bytes",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        audio_bytes = await response.read()
                        logger.info(f"Cartesia TTS success: {len(audio_bytes)} bytes")
                        return base64.b64encode(audio_bytes).decode()
                    else:
                        error_text = await response.text()
                        logger.error(f"Cartesia TTS error {response.status}: {error_text}")
                        return None

        except Exception as e:
            logger.error(f"Error synthesizing speech with Cartesia: {e}", exc_info=True)
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
    logger.info("Using: Deepgram STT + OpenAI LLM + Cartesia TTS + Web Scraping")

    server = VoiceServer()
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
