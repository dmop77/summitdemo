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

    # Pulpoo API (task creation)
    pulpoo_api_key: str = Field(
        default="",
        description="Pulpoo API key"
    )
    pulpoo_api_url: str = Field(
        default="https://api.pulpoo.com/v1/external/tasks/create",
        description="Pulpoo API endpoint"
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
        default="""You are a friendly and professional support agent for Pulpoo.

Your responsibilities:
1. Greet users warmly and professionally
2. Listen actively to understand their needs
3. Collect relevant contact information
4. Help schedule meetings or create support tickets
5. Summarize issues clearly and concisely

Guidelines:
- Be conversational and helpful
- Keep responses under 100 words
- Ask clarifying questions when needed
- Use the create_task tool to log important issues""",
        description="System prompt for the agent"
    )

    max_conversation_history: int = Field(
        default=20,
        description="Maximum messages to keep in conversation history"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_voice_config() -> VoiceConfig:
    """Get voice configuration from environment."""
    return VoiceConfig()


def get_agent_config() -> AgentConfig:
    """Get agent configuration from environment."""
    return AgentConfig()
