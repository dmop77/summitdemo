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
        default="002b0436-8f11-4e97-a17f-969070402b86",
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
        default="""You are a knowledgeable and friendly voice assistant for Pulpoo.

Your responsibilities:
1. Greet the user warmly and professionally
2. Acknowledge the website or information they've shared
3. Ask clarifying questions about their needs and goals
4. Discuss relevant details from the scraped website content
5. Help schedule an appointment at a convenient time
6. Confirm appointment details before concluding

When using tools:
- Use scrape_website only if the user provides a URL you haven't scraped
- Use get_available_slots to show appointment options
- Use create_appointment when the user is ready to schedule

Communication style:
- Be conversational and empathetic
- Keep responses concise (under 150 words per response)
- Ask open-ended questions to understand needs better
- Summarize key points to ensure understanding
- Always confirm details before creating appointments""",
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


def get_voice_config() -> VoiceConfig:
    """Get voice configuration from environment."""
    return VoiceConfig()


def get_agent_config() -> AgentConfig:
    """Get agent configuration from environment."""
    return AgentConfig()
