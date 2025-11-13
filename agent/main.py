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
import time
from typing import Optional

from dotenv import load_dotenv
import aiohttp
from aiohttp import web
from deepgram import DeepgramClient
from openai import AsyncOpenAI

# Load environment variables from .env file
load_dotenv()

from config import get_voice_config, get_audio_config
from voice_agent import BackgroundAgent, ConversationState
from web_scraper import WebScraper
from db_client import SupabaseClient

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
        self.audio_config = get_audio_config()
        self.agent = BackgroundAgent()
        self.web_scraper = WebScraper(self.config.openai_api_key)
        self.app = web.Application()
        self.sessions = {}  # Store session data

        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        self.db = None
        if supabase_url and supabase_key:
            try:
                self.db = SupabaseClient(supabase_url, supabase_key)
                logger.info("✓ Database client connected")
            except Exception as e:
                logger.warning(f"⚠️ Database connection failed: {e}")
        else:
            logger.warning("⚠️ SUPABASE_URL or SUPABASE_KEY not set - caching disabled")

        self._setup_routes()

    def _create_wav_header(self, audio_bytes: bytes, sample_rate: int = None, channels: int = None,
                          sample_width: int = None) -> bytes:
        """
        Create WAV file header for PCM16 audio data.

        Args:
            audio_bytes: Raw PCM16 audio data
            sample_rate: Sample rate in Hz (default from config)
            channels: Number of channels (default from config)
            sample_width: Bytes per sample (default from config)

        Returns:
            Complete WAV file with headers
        """
        # Use config defaults if not provided
        sample_rate = sample_rate or self.audio_config.sample_rate
        channels = channels or self.audio_config.channels
        sample_width = sample_width or self.audio_config.sample_width

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

            # Save to database
            db_user_id = None
            if self.db:
                try:
                    # Get or create user
                    user = await self.db.get_or_create_user(
                        email=email,
                        name=name,
                        website_url=website_url
                    )
                    db_user_id = user.get("id")

                    # Create session record
                    website_summary = None
                    if scraped_content and hasattr(scraped_content, 'summary'):
                        website_summary = scraped_content.summary

                    session = await self.db.create_session(
                        user_id=db_user_id,
                        session_id=session_id,
                        website_summary=website_summary
                    )

                    # Save scraped content if available
                    if scraped_content:
                        await self.db.save_scraped_content(
                            user_id=db_user_id,
                            session_id=session.get("id"),
                            url=website_url,
                            title=scraped_content.title if hasattr(scraped_content, 'title') else "",
                            summary=scraped_content.summary if hasattr(scraped_content, 'summary') else "",
                            content=scraped_content.content if hasattr(scraped_content, 'content') else ""
                        )

                    logger.info(f"✓ Saved user and session to database: {db_user_id}")
                except Exception as e:
                    logger.error(f"⚠️ Error saving to database: {e}")

            # Initialize voice assistant with user context
            self.agent.set_user_info(name, email, website_url)

            # Set scraped content if available
            if scraped_content:
                # Update context with the scraped content summary
                # Extract the summary string from the ScrapedContent object
                summary = scraped_content.summary if scraped_content.summary else scraped_content.content
                self.agent.update_context_with_scraped_content(summary)
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

    async def _send_greeting_and_overview(self, ws: web.WebSocketResponse) -> str:
        """
        Send greeting, overview, and engagement question automatically.
        Runs in background - user can speak anytime (interrupts or waits).

        Args:
            ws: WebSocket connection

        Returns:
            Empty string (for background task)
        """
        try:
            if self.agent.conversation_context and self.agent.conversation_context.user_info:
                user = self.agent.conversation_context.user_info

                # Step 1: Send greeting with name
                # Clean up URL for speech (remove https://, trailing slash)
                domain = str(user.website_url).replace("https://", "").replace("http://", "").rstrip("/")
                greeting = f"Hi {user.name}! Thanks for joining me today."
                logger.info(f"📢 Sending greeting: {greeting}")

                await ws.send_json({
                    "type": "response.text",
                    "text": greeting,
                })

                # Try greeting audio (5 second timeout - Cartesia can be slow)
                try:
                    audio_data = await asyncio.wait_for(
                        self._synthesize_speech(greeting),
                        timeout=5.0
                    )
                    if audio_data:
                        await ws.send_json({
                            "type": "response.audio.delta",
                            "delta": audio_data,
                        })
                        await ws.send_json({
                            "type": "response.audio.done",
                        })
                        logger.info("✓ Greeting audio sent")
                except asyncio.TimeoutError:
                    logger.warning("⚠️  Greeting audio timeout (5s) - continuing")
                except Exception as e:
                    logger.warning(f"Greeting audio error: {e}")

                # Small delay before overview
                await asyncio.sleep(0.3)

                # Step 2: Send detailed overview of what we learned from scraping
                website_summary = ""
                logger.info(f"Debug: user.website_summary = {getattr(user, 'website_summary', 'NOT SET')}")

                if hasattr(user, 'website_summary') and user.website_summary:
                    if isinstance(user.website_summary, str):
                        website_summary = user.website_summary[:250]  # More content for overview
                        logger.info(f"Using string summary: {website_summary[:100]}...")
                    else:
                        if hasattr(user.website_summary, 'summary'):
                            website_summary = str(user.website_summary.summary)[:250]
                            logger.info(f"Using object.summary: {website_summary[:100]}...")
                        else:
                            website_summary = str(user.website_summary)[:250]
                            logger.info(f"Using str(object): {website_summary[:100]}...")
                else:
                    logger.warning("⚠️  No website_summary found - will send generic overview")
                    website_summary = "I've reviewed your website and I'm impressed with what you're doing."

                # Build comprehensive overview
                overview = f"""I've reviewed your website at {domain} and here's what I learned about your business:

{website_summary}

I think there's a lot of potential here. I'd love to discuss your goals, challenges, and how we might be able to help you achieve them. Would you be open to scheduling a brief call to explore this further?"""
                logger.info(f"📝 Sending overview: {overview[:100]}...")

                await ws.send_json({
                    "type": "response.text",
                    "text": overview,
                })
                logger.info("✓ Overview text sent to client")

                # Try overview audio (10 second timeout - longer text, needs enough time)
                overview_sent = False
                try:
                    logger.info(f"Starting overview audio synthesis for {len(overview)} chars...")
                    audio_data = await asyncio.wait_for(
                        self._synthesize_speech(overview),
                        timeout=10.0
                    )
                    if audio_data:
                        await ws.send_json({
                            "type": "response.audio.delta",
                            "delta": audio_data,
                        })
                        await ws.send_json({
                            "type": "response.audio.done",
                        })
                        logger.info(f"✓ Overview audio sent ({len(audio_data)} bytes)")
                        overview_sent = True
                    else:
                        logger.warning("⚠️  Overview audio synthesis returned no data")
                except asyncio.TimeoutError:
                    logger.warning("⚠️  Overview audio timeout (10s) - continuing without audio")
                except Exception as e:
                    logger.warning(f"Overview audio error: {e}", exc_info=True)

            return ""

        except Exception as e:
            logger.error(f"Error in greeting and overview: {e}", exc_info=True)
            return ""

    async def _send_greeting(self, user_name: str, ws: web.WebSocketResponse) -> str:
        """
        Send an automatic greeting to the user when voice session starts.
        Non-blocking: does not prevent user audio processing.

        Args:
            user_name: User's name
            ws: WebSocket connection

        Returns:
            Greeting message text
        """
        try:
            # Generate greeting from agent (synchronous - no await needed)
            greeting_response = self.agent.get_greeting()

            if not greeting_response:
                logger.warning("_send_greeting: No greeting generated or already sent")
                return ""

            logger.info(f"_send_greeting: Generated greeting: {greeting_response}")

            # Send greeting text immediately (non-blocking)
            try:
                await ws.send_json({
                    "type": "response.text",
                    "text": greeting_response,
                })
                logger.info("_send_greeting: Text sent successfully")
            except Exception as e:
                logger.warning(f"_send_greeting: Failed to send text: {e}")

            # Try to synthesize audio with short timeout (2 seconds max)
            # If it fails, continue without audio - user can still hear greeting text
            try:
                audio_data = await asyncio.wait_for(
                    self._synthesize_speech(greeting_response),
                    timeout=2.0  # Short timeout for greeting
                )
                if audio_data:
                    await ws.send_json({
                        "type": "response.audio.delta",
                        "delta": audio_data,
                    })
                    await ws.send_json({
                        "type": "response.audio.done",
                    })
                    logger.info("_send_greeting: Audio sent successfully")
            except asyncio.TimeoutError:
                logger.warning("_send_greeting: Audio synthesis timeout (2s) - continuing without audio")
            except Exception as e:
                logger.warning(f"_send_greeting: Audio synthesis error: {e}")

            return greeting_response

        except Exception as e:
            logger.error(f"_send_greeting: Error sending greeting: {e}", exc_info=True)
            return ""

    async def _process_utterance(self, complete_audio: bytes, ws: web.WebSocketResponse,
                                session_id: str, dg_client) -> bool:
        """
        Process a complete utterance: transcribe it and generate agent response.
        Uses OpenAI Whisper for faster transcription, Deepgram for VAD only.

        Args:
            complete_audio: Raw PCM16 audio bytes
            ws: WebSocket connection
            session_id: Session ID
            dg_client: Deepgram client (for future VAD use)

        Returns:
            True if successful, False otherwise
        """
        try:
            import time
            start_time = time.time()
            logger.info(f"🎤 Processing utterance: {len(complete_audio)} bytes")

            # Create WAV file from complete audio for Whisper
            complete_wav = self._create_wav_header(
                complete_audio,
                sample_rate=24000,
                channels=1,
                sample_width=2
            )
            logger.debug(f"   WAV header created in {time.time()-start_time:.2f}s")

            # Transcribe with OpenAI Whisper (faster than Deepgram for this use case)
            client = AsyncOpenAI(api_key=self.config.openai_api_key)

            # Convert WAV to bytes buffer for Whisper API
            from io import BytesIO
            audio_buffer = BytesIO(complete_wav)
            audio_buffer.name = "audio.wav"

            stt_start = time.time()
            transcript_response = await client.audio.transcriptions.create(
                model=self.audio_config.stt_model,
                file=audio_buffer,
                language="en",
            )
            stt_time = time.time() - stt_start
            logger.info(f"   Whisper STT: {stt_time:.2f}s")

            final_transcript = transcript_response.text.strip() if transcript_response.text else ""

            if not final_transcript:
                logger.warning("⚠️  No transcript generated from audio")
                return False

            logger.info(f"✓ Transcribed: '{final_transcript[:80]}...'" if len(final_transcript) > 80 else f"✓ Transcribed: '{final_transcript}'")

            # Save user message to database
            if self.db and session_id in self.sessions:
                try:
                    session_data = self.sessions[session_id]
                    user = await self.db.get_or_create_user(
                        email=session_data.get("email", ""),
                        name=session_data.get("name", ""),
                        website_url=session_data.get("website_url", "")
                    )
                    session = await self.db.get_session(session_id)
                    if session:
                        await self.db.save_message(
                            session_id=session.get("id"),
                            user_id=user.get("id"),
                            sender="user",
                            message_text=final_transcript,
                            transcript=final_transcript
                        )
                except Exception as e:
                    logger.warning(f"⚠️ Error saving user message: {e}")

            # Send transcript to client immediately
            await ws.send_json({
                "type": "user.transcript",
                "text": final_transcript,
            })

            # Get agent response
            import time
            llm_start = time.time()
            response_text = await self.agent.process_message(
                final_transcript, session_id
            )
            llm_time = time.time() - llm_start
            logger.info(f"   LLM response: {llm_time:.2f}s")

            # If response is empty, conversation is completed - disconnect
            if not response_text or not response_text.strip():
                logger.info("🏁 Conversation completed. Hanging up.")
                await ws.send_json({"type": "session.close"})
                return True

            logger.info(f"✓ Agent: '{response_text[:80]}...'" if len(response_text) > 80 else f"✓ Agent: '{response_text}'")

            # Save agent message to database
            if self.db and session_id in self.sessions:
                try:
                    session_data = self.sessions[session_id]
                    user = await self.db.get_or_create_user(
                        email=session_data.get("email", ""),
                        name=session_data.get("name", ""),
                        website_url=session_data.get("website_url", "")
                    )
                    session = await self.db.get_session(session_id)
                    if session:
                        await self.db.save_message(
                            session_id=session.get("id"),
                            user_id=user.get("id"),
                            sender="agent",
                            message_text=response_text
                        )
                except Exception as e:
                    logger.warning(f"⚠️ Error saving agent message: {e}")

            # Send agent response immediately
            await ws.send_json({
                "type": "response.text",
                "text": response_text,
            })

            # Synthesize speech with Cartesia - optimized with timeout
            tts_start = time.time()
            try:
                audio_data = await asyncio.wait_for(
                    self._synthesize_speech(response_text),
                    timeout=8.0  # Timeout after 8 seconds to prevent blocking
                )
                tts_time = time.time() - tts_start
                logger.info(f"   Cartesia TTS: {tts_time:.2f}s")
            except asyncio.TimeoutError:
                logger.warning(f"⚠️  TTS timeout after {time.time()-tts_start:.2f}s - sending without audio")
                audio_data = None

            if audio_data:
                logger.info(f"✓ Audio synthesized: {len(audio_data)} bytes")
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

            return True

        except asyncio.TimeoutError:
            logger.warning("TTS synthesis timed out - continuing without audio")
            return True
        except Exception as e:
            logger.error(f"Error processing utterance: {e}", exc_info=True)
            return False

    async def _websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections for voice streaming."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Retrieve session_id from URL query parameters
        session_id = request.rel_url.query.get('session_id', f"session_{id(ws)}")
        logger.info(f"New WebSocket connection: {session_id}")

        greeting_sent = False

        # Audio accumulation for complete utterances
        audio_buffer = []
        last_speech_time = 0  # Track when speech was last detected
        SPEECH_TIMEOUT = 1.0  # Wait 1.0 seconds of silence after speech detected before processing (reduced from 1.5 for lower latency)
        MIN_ACCUMULATION_TIME = 0.25  # Minimum audio to accumulate before checking (250ms, reduced from 500ms)

        try:
            # Initialize voice assistant
            await self.agent.initialize()

            # Restore session data if available (from setup phase)
            if session_id in self.sessions:
                session_data = self.sessions[session_id]
                logger.info(f"Restoring session context for {session_data.get('name')}")
                self.agent.set_user_info(
                    name=session_data.get("name", ""),
                    email=session_data.get("email", ""),
                    website_url=session_data.get("website_url", ""),
                    website_summary=session_data.get("scraped_content", "")
                )
            else:
                # Reset conversation history for this new session if no session data
                self.agent.reset_conversation()

            # Connect to Deepgram for STT
            dg_client = DeepgramClient(api_key=self.config.deepgram_api_key)

            # Send greeting and overview in background (non-blocking)
            greeting_task = None
            greeting_start_time = None

            # Track if user is currently speaking (turn detection)
            user_is_speaking = False
            last_speech_start = None

            if self.agent.conversation_context and self.agent.conversation_context.user_info and not greeting_sent:
                logger.info(f"Sending greeting to {self.agent.conversation_context.user_info.name}")
                greeting_start_time = time.time()
                greeting_task = asyncio.create_task(
                    self._send_greeting_and_overview(ws)
                )
                greeting_sent = True

            # Track when greeting is truly ready (after task completes AND audio finishes)
            greeting_audio_finished_at = None

            # Track if we're currently processing an LLM response (for interruption)
            current_response_task = None

            # Listen for messages from browser
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    # Handle interruption signal from client
                    if data.get("type") == "input_audio_buffer.speech_started":
                        logger.info("🛑 User started speaking - cancelling any pending response")
                        # Cancel the current LLM response task if one is running
                        if current_response_task and not current_response_task.done():
                            current_response_task.cancel()
                            logger.info("✓ Cancelled LLM response task")
                        continue

                    # Handle audio data
                    if data.get("type") == "input_audio_buffer.append":
                        # Don't process user audio until greeting is fully done
                        should_wait_for_greeting = False

                        if greeting_task and not greeting_task.done():
                            # Greeting still sending messages
                            logger.debug(f"⏸️ Greeting task still running, buffering audio...")
                            should_wait_for_greeting = True
                        elif greeting_task and greeting_task.done() and greeting_audio_finished_at is None:
                            # Greeting task done, but need to wait for audio to finish playing
                            # Assume 15 seconds total for greeting + overview audio playback
                            elapsed_since_greeting_started = time.time() - greeting_start_time if greeting_start_time else 0

                            # Wait minimum 15 seconds before accepting user input
                            if elapsed_since_greeting_started < 15.0:
                                logger.debug(f"⏸️ Greeting audio still playing ({elapsed_since_greeting_started:.1f}s/15.0s), buffering audio...")
                                should_wait_for_greeting = True
                            else:
                                # Greeting audio should be finished now
                                logger.info(f"✓ Greeting + audio complete ({elapsed_since_greeting_started:.1f}s), accepting user input")
                                greeting_task = None
                                greeting_audio_finished_at = time.time()
                                # Clear any audio accumulated during greeting
                                audio_buffer = []
                                last_speech_time = 0
                                logger.info("🔄 Audio buffer cleared - ready for fresh user input")

                        if should_wait_for_greeting:
                            continue

                        # Mark that user is currently speaking (turn detection)
                        user_is_speaking = True
                        if last_speech_start is None:
                            last_speech_start = time.time()
                            logger.debug("👂 User started speaking")

                        audio_b64 = data.get("audio", "")
                        if audio_b64:
                            current_time = time.time()

                            # Decode base64 to get raw PCM16 bytes
                            raw_audio_bytes = base64.b64decode(audio_b64)

                            # Initialize last_speech_time on first chunk
                            if not audio_buffer:
                                last_speech_time = current_time

                            # Add to buffer for accumulation
                            audio_buffer.append(raw_audio_bytes)

                            # Get accumulated audio size
                            total_audio_size = sum(len(chunk) for chunk in audio_buffer)

                            # If we have minimal audio, wait for more
                            if total_audio_size < 24000 * 2 * 0.5:  # Less than 500ms of audio
                                continue

                            # Check if enough silence has passed since first audio chunk
                            silence_duration = current_time - last_speech_time

                            # Only process if we have 1.5+ seconds of silence
                            should_process = silence_duration >= SPEECH_TIMEOUT and total_audio_size > 0

                            if should_process:
                                # Concatenate all accumulated audio
                                complete_audio = b''.join(audio_buffer)
                                logger.info(f"🎤 Processing utterance: {len(complete_audio)} bytes (user stopped speaking, {silence_duration:.2f}s silence)")

                                # Process utterance and send response
                                success = await self._process_utterance(
                                    complete_audio, ws, session_id, dg_client
                                )

                                # Reset accumulation
                                audio_buffer = []
                                last_speech_time = 0

                                # If conversation ended, break
                                if success and self.agent.state == ConversationState.COMPLETED:
                                    break

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")

        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
        finally:
            await self.agent.cleanup()
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
            logger.info(f"Synthesizing speech: {text[:100]}...")

            # Use OpenAI TTS
            client = AsyncOpenAI(api_key=self.config.openai_api_key)

            response = await client.audio.speech.create(
                model="tts-1",  # Fast real-time TTS
                voice="echo",   # Professional voice
                input=text,
                response_format="pcm"  # Raw PCM format for compatibility
            )

            # Get audio bytes from response
            audio_bytes = await response.aread()
            logger.info(f"✓ OpenAI TTS success: {len(audio_bytes)} bytes")
            return base64.b64encode(audio_bytes).decode()

        except Exception as e:
            logger.error(f"Error synthesizing speech with OpenAI TTS: {e}", exc_info=True)
            return None

    async def start(self):
        """Start the server with proper socket reuse handling."""
        # Wait a moment to ensure TIME_WAIT sockets are released
        await asyncio.sleep(1)
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                site = web.TCPSite(
                    runner,
                    self.config.host,
                    self.config.port,
                    reuse_address=True,
                    reuse_port=False
                )
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
                
                return
                
            except OSError as e:
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"Port {self.config.port} not ready (attempt {retry_count}/{max_retries}), retrying in 2s...")
                    await runner.cleanup()
                    await asyncio.sleep(2)
                    runner = web.AppRunner(self.app)
                    await runner.setup()
                else:
                    logger.error(f"Failed to start server after {max_retries} attempts: {e}")
                    await runner.cleanup()
                    raise


async def main():
    """Main entry point."""
    logger.info("Starting Voice Agent Server")
    logger.info("Using: OpenAI Whisper STT + OpenAI LLM + OpenAI TTS + Web Scraping")

    server = VoiceServer()
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
