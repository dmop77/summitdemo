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
        description="OpenAI LLM model"
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
        default="a167e0f3-df7e-4d52-a9c3-f949145efdab",
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

IMPORTANT CONVERSATION FLOW:
1. When you receive "start" as the first message, this means greet the user warmly by name and ask how you can help them schedule a meeting
2. After the initial greeting, STOP greeting and focus on the conversation - listen to what the user is saying
3. Collect the TOPIC: If not provided, ask "What's this meeting about?" or "What would you like to discuss?"
4. Collect the DATE and TIME: Ask "When works best for you?" or offer available slots using get_available_slots tool
5. CONFIRM all details: "So I'm scheduling a [TOPIC] meeting on [DATE] at [TIME]. Is that correct?"
6. Only after confirmation, use create_appointment tool with the collected information
7. Provide a clear confirmation: "Perfect! Your appointment for [TOPIC] is scheduled for [DATE] at [TIME]"

WHEN USING TOOLS:
- Use get_available_slots to show available times and help the user choose
- Only use create_appointment when you have confirmed:
  * Topic of the meeting (required)
  * Preferred date and time (required - should be in ISO format like "2025-11-15T14:30:00" or as natural language like "next Monday at 2 PM")
  * User's explicit confirmation (required)
- For create_appointment, pass the topic and preferred_date/time clearly
- Example: If user says "I'd like to meet next Monday at 2 PM about website optimization", you should call create_appointment with topic="website optimization" and preferred_date describing the date/time

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


def get_agent_config() -> AgentConfig:
    """Get agent configuration from environment."""
    return AgentConfig()
