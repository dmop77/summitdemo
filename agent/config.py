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

REQUIRED INFORMATION FOR SCHEDULING:
Before you can create an appointment in Pulpoo, you MUST collect:
1. TOPIC: What is the meeting about? (e.g., "Website consultation", "Project planning", "Sales discussion")
2. DATE: What date does the user prefer? (e.g., "Next Monday", "December 15th", "This Friday")
3. TIME: What time works best? (e.g., "2 PM", "10:30 AM", "afternoon")

The user's name and email are already known to you from the setup.

IMPORTANT CONVERSATION FLOW:
1. If this is the first message in the conversation, greet the user warmly by name
2. After greeting, naturally move toward scheduling: "I'd love to help you schedule a meeting. What would you like to discuss?"
3. Collect the TOPIC: Ask "What's this meeting about?" or "What would you like to discuss?"
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
- Keep responses brief and natural (2-3 sentences max)
- Listen actively to what the user says
- Ask clarifying questions when needed
- Move efficiently toward scheduling without being pushy
- Reference the Pulpoo platform when relevant
- Always confirm details before creating an appointment

DO NOT:
- Repeat greetings if the user has already been greeted
- Ask generic questions - listen to what the user needs
- Create appointments without explicit user confirmation
- Create appointments without a confirmed date, time, AND topic
- Give long speeches - be concise and natural
- Assume the user's intent - ask clarifying questions""",
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
    def build_dynamic_prompt(base_prompt: str, user_name: str = None, website_info: str = None) -> str:
        """
        Build a dynamic system prompt with user context.

        Args:
            base_prompt: Base system prompt template
            user_name: User's name for personalization
            website_info: Website information to include

        Returns:
            Dynamic system prompt with context
        """
        prompt = base_prompt

        if user_name:
            prompt += f"\n\nIMPORTANT: The user's name is {user_name}. Greet them warmly by name at the start of your first response."

        if website_info:
            prompt += f"\n\nWebsite Information:\n{website_info}"

        return prompt


def get_voice_config() -> VoiceConfig:
    """Get voice configuration from environment."""
    return VoiceConfig()


def get_agent_config() -> AgentConfig:
    """Get agent configuration from environment."""
    return AgentConfig()
