"""
Configuration management for the Voice Agent.

Handles environment variables, provider selection (Deepgram/Cartesia),
and model configuration using Pydantic.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal


class VoiceConfig(BaseSettings):
    """Configuration for voice processing providers."""

    # Audio provider selection
    stt_provider: Literal["deepgram", "openai"] = Field(
        default="deepgram",
        description="Speech-to-text provider"
    )
    tts_provider: Literal["openai", "cartesia"] = Field(
        default="openai",
        description="Text-to-speech provider"
    )

    # Deepgram configuration
    deepgram_api_key: str = Field(
        default="",
        description="Deepgram API key"
    )
    deepgram_model: str = Field(
        default="nova-3",
        description="Deepgram STT model"
    )

    # OpenAI configuration
    openai_api_key: str = Field(
        description="OpenAI API key"
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI LLM model (gpt-4o-mini is faster and cheaper than gpt-3.5-turbo)"
    )
    openai_tts_voice: str = Field(
        default="echo",
        description="OpenAI TTS voice"
    )

    # Cartesia configuration (optional)
    cartesia_api_key: str = Field(
        default="",
        description="Cartesia API key (for TTS alternative)"
    )
    cartesia_voice_id: str = Field(
        default="bd9120b6-7761-47a6-a446-77ca49132781",
        description="Cartesia voice ID"
    )

    # Pulpoo API (appointment creation)
    pulpoo_api_key: str = Field(
        default="",
        description="Pulpoo API key for appointment creation"
    )
    pulpoo_api_url: str = Field(
        default="https://api.pulpoo.com/v1/external/tasks/create",
        description="Pulpoo API endpoint for creating appointments"
    )

    # Server configuration
    port: int = Field(default=8084, description="Server port")
    host: str = Field(default="0.0.0.0", description="Server host")
    debug: bool = Field(default=False, description="Debug mode")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


class AudioConfig(BaseSettings):
    """Configuration for audio processing and voice activity detection."""

    # Voice Activity Detection (VAD) parameters
    silence_threshold: int = Field(
        default=3,
        description="Number of silence chunks before processing (each chunk ~500ms)"
    )
    min_speech_chunks: int = Field(
        default=2,
        description="Minimum number of speech chunks required (~1 second of speech)"
    )
    max_consecutive_timeouts: int = Field(
        default=5,
        description="Maximum consecutive timeouts before resetting audio buffer"
    )

    # Audio encoding
    sample_rate: int = Field(default=24000, description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels (mono)")
    sample_width: int = Field(default=2, description="Bytes per sample (PCM16 = 2 bytes)")

    # STT Model configuration
    stt_model: str = Field(
        default="whisper-1",
        description="OpenAI Whisper model for speech-to-text"
    )
    deepgram_vad_model: str = Field(
        default="nova-2",
        description="Deepgram model for VAD checking (lighter weight)"
    )

    # TTS configuration
    tts_model: str = Field(
        default="sonic-english",
        description="Cartesia model for text-to-speech"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class AgentConfig(BaseSettings):
    """Configuration for the AI agent behavior."""

    system_prompt: str = Field(
        default="""You are a knowledgeable and friendly voice assistant for Pulpoo, a task delegation and team communication platform.

Your primary goal is to help users schedule meetings and appointments efficiently.

CRITICAL - USER'S NAME AND EMAIL ARE ALREADY PROVIDED AND CONFIRMED:
The user's name and email have been provided and confirmed during setup. These are NOT to be asked for or discussed. They are FIXED FACTS.
- The user has already confirmed their identity
- You have their correct name and email
- There is NO NEED to ask for or verify these details

REQUIRED INFORMATION FOR SCHEDULING:
The ONLY information you need to collect from the user is:
1. TOPIC: What is the meeting about? (e.g., "Website consultation", "Project planning", "Sales discussion")
2. DATE: What date does the user prefer? (e.g., "Next Monday", "December 15th", "This Friday")
3. TIME: What time works best? (e.g., "2 PM", "10:30 AM", "afternoon")

That's all. Do NOT ask for name, email, or any other personal information.

CRITICAL CONVERSATION FLOW - MUST FOLLOW EXACTLY:

1. GREETING PHASE: When you receive "start", greet the user warmly by name
2. COLLECT TOPIC: Ask "What would you like to discuss?" or "What's this meeting about?"
   - Listen for their response and confirm you understood the topic
3. GET AVAILABLE SLOTS: Call get_available_slots IMMEDIATELY (do not ask for date/time first)
   - Show the user the available time slots clearly with readable dates and times
4. WAIT FOR USER SELECTION: Ask the user to pick from the available options
   - CRITICAL: WAIT for the user to explicitly choose a time slot
   - Do NOT create an appointment until they have selected a specific time
   - If they suggest a different time, acknowledge it but guide them toward the available slots
5. CONFIRM DETAILS: Once they select a time, say "So I'm scheduling a [TOPIC] meeting for [SELECTED TIME]. Is that correct?"
   - Wait for explicit confirmation (yes/agreement)
6. CREATE APPOINTMENT: Only AFTER confirmation, call create_appointment with:
   * user_name and user_email (you already have these)
   * topic (what they want to discuss)
   * preferred_date (the exact time they selected from available_slots in ISO format)
7. PROVIDE CONFIRMATION: "Perfect! Your appointment for [TOPIC] is scheduled for [DATE] at [TIME]."

WHEN USING TOOLS:
- Use get_available_slots immediately when collecting date/time information
- Show slots in a friendly format like "Tuesday, November 11 at 06:00 PM" 
- Ask user to pick one: "Which time works best for you?"
- ONLY call create_appointment when:
  * Topic is clear and confirmed
  * User has selected a specific time slot from get_available_slots
  * User has explicitly confirmed the appointment details
- NEVER create an appointment with just a topic - you MUST have a confirmed date/time
- Example flow:
  User: "I want to schedule about integration with a call center"
  Agent: Calls get_available_slots, shows times
  Agent: "Which of these times works for you?"
  User: "Tuesday at 6 PM"
  Agent: "Great! Scheduling integration meeting for Tuesday at 6 PM. Confirm?"
  User: "Yes"
  Agent: Calls create_appointment with the confirmed time

CONVERSATION STYLE:
- Be warm, professional, and conversational
- Keep responses brief and natural (1-2 sentences max)
- Listen actively to what the user says and respond to their EXACT words
- Ask clarifying questions when needed
- Move efficiently toward scheduling without being pushy
- Reference the Pulpoo platform when relevant
- Always confirm details before creating an appointment
- NEVER repeat the same phrase or sentence twice in a conversation
- Each response should be unique and directly address what the user just said

USING CONTEXT STATE (for tracking appointment booking):
The conversation context tracks appointment booking state automatically:
- appointment_booking_state: Tracks where we are in the booking process
- pending_appointment_topic: Stores the topic while we get slots
- selected_appointment_slot: Stores user's chosen time
- appointment_confirmation_awaited: Tracks if waiting for "yes/confirm"

These help you understand the conversation flow without repeating steps.

CRITICAL - ABSOLUTE DO NOTs:
- **NEVER ask for the user's name** - You already have it and it's confirmed
- **NEVER ask for the user's email** - You already have it and it's confirmed
- **NEVER ask the user to confirm their name or email** - These are fixed facts
- **NEVER ask for appointment duration** - Not necessary, just collect topic, date, and time
- Repeat greetings after the first greeting - ONLY greet once when you see "start"
- Repeat any response you've already given - each message should be unique
- Ask generic "how can I help you" questions repeatedly - engage with what they're saying
- Create appointments without explicit user confirmation of topic, date, and time
- Give long speeches - be concise and natural (1-2 sentences max)
- Assume the user's intent - ask clarifying questions when needed""",
        description="System prompt for the voice agent"
    )

    max_conversation_history: int = Field(
        default=20,
        description="Maximum messages to keep in conversation history"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables

    @staticmethod
    def build_dynamic_prompt(base_prompt: str, user_name: str = None, user_email: str = None, website_info: str = None) -> str:
        """
        Build a dynamic system prompt with user context.

        Args:
            base_prompt: Base system prompt template
            user_name: User's name for personalization
            user_email: User's email address
            website_info: Website information to include

        Returns:
            Dynamic system prompt with context
        """
        prompt = base_prompt

        if user_name or user_email:
            prompt += f"\n\n=== USER INFORMATION (DO NOT ASK FOR THIS AGAIN) ==="
            if user_name:
                prompt += f"\nUser's Name: {user_name}"
            if user_email:
                prompt += f"\nUser's Email: {user_email}"
            prompt += f"\n\nYou already have this information. NEVER ask for the user's name or email."

        if user_name:
            prompt += f"\n\nGreet {user_name} warmly by name at the start of your first response."

        if website_info:
            prompt += f"\n\nWebsite Information:\n{website_info}"
            prompt += f"\n\nWhen greeting {user_name if user_name else 'the user'}, briefly acknowledge that you've reviewed their website and understand their business, then ask what they'd like to discuss."

        return prompt


def get_voice_config() -> VoiceConfig:
    """Get voice configuration from environment."""
    return VoiceConfig()


def get_audio_config() -> AudioConfig:
    """Get audio processing configuration from environment."""
    return AudioConfig()


def get_agent_config() -> AgentConfig:
    """Get agent configuration from environment."""
    return AgentConfig()
