"""
Voice Agent using Pydantic AI with Deepgram STT and OpenAI LLM.

Features:
- Deepgram speech-to-text
- OpenAI GPT-4o-mini for intelligent responses
- OpenAI or Cartesia TTS for speech synthesis
- Web scraping with semantic embeddings
- Appointment scheduling via Pulpoo
- Real-time audio streaming
"""

import logging
from typing import Optional

import aiohttp
from pydantic_ai import Agent, RunContext, ModelSettings
from pydantic_ai.models.openai import OpenAIChatModel

from config import get_voice_config, get_agent_config
from schemas import VoiceAgentMessage, ConversationContext, UserInfo
from agent_tools import AgentTools

logger = logging.getLogger(__name__)


class VoiceAssistant:
    """Main voice agent using Pydantic AI with integrated tools."""

    def __init__(self):
        """Initialize the voice assistant."""
        self.voice_config = get_voice_config()
        self.agent_config = get_agent_config()
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.tools = AgentTools(
            openai_api_key=self.voice_config.openai_api_key,
            deepgram_api_key=self.voice_config.deepgram_api_key,
            pulpoo_api_key=self.voice_config.pulpoo_api_key,
        )
        self.agent = self._create_agent()
        self.conversation_context: Optional[ConversationContext] = None

    def _create_agent(self) -> Agent:
        """
        Create the Pydantic AI agent with tools and system prompt.

        Returns:
            Configured Agent instance
        """
        # Initialize the OpenAI model with ModelSettings for temperature
        model = OpenAIChatModel(
            model_name=self.voice_config.openai_model,
            settings=ModelSettings(temperature=0.7),
        )

        # Create agent with system instructions
        agent = Agent(
            model=model,
            system_prompt=self.agent_config.system_prompt,
            tools=[
                self.tools.scrape_website,
                self.tools.create_appointment,
                self.tools.get_available_slots,
            ],
        )

        return agent

    async def initialize(self):
        """Initialize the agent (set up HTTP session, etc.)."""
        self.http_session = aiohttp.ClientSession()
        logger.info("Voice Assistant initialized")

    async def cleanup(self):
        """Clean up resources."""
        if self.http_session:
            await self.http_session.close()
        logger.info("Voice Assistant cleaned up")

    async def process_message(self, user_input: str, session_id: str) -> str:
        """
        Process a user message and return agent response.

        Args:
            user_input: The user's message text
            session_id: Unique conversation session ID

        Returns:
            Agent's response text
        """
        try:
            # Initialize conversation context if needed
            if self.conversation_context is None:
                self.conversation_context = ConversationContext(session_id=session_id)

            # Add user message to history
            user_msg = VoiceAgentMessage(
                message_id=f"msg_{len(self.conversation_context.conversation_history)}",
                session_id=session_id,
                speaker="user",
                text=user_input,
            )
            self.conversation_context.conversation_history.append(user_msg)

            logger.info(f"User message: {user_input}")

            # Get agent response with context
            response = await self.agent.run(
                user_input,
                deps=RunContext(deps={"session_id": session_id, "context": self.conversation_context}),
            )

            response_text = response.data
            logger.info(f"Agent response: {response_text}")

            # Add agent message to history
            agent_msg = VoiceAgentMessage(
                message_id=f"msg_{len(self.conversation_context.conversation_history)}",
                session_id=session_id,
                speaker="agent",
                text=response_text,
            )
            self.conversation_context.conversation_history.append(agent_msg)

            return response_text

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return "I encountered an error processing your request. Could you please repeat that?"

    def update_context_with_user_info(self, name: str, email: str, website_url: str):
        """
        Update conversation context with user information.

        Args:
            name: User's name
            email: User's email
            website_url: Website URL to scrape
        """
        # Initialize context if needed
        if self.conversation_context is None:
            import uuid
            self.conversation_context = ConversationContext(session_id=str(uuid.uuid4()))

        self.conversation_context.user_info = UserInfo(
            name=name,
            email=email,
            website_url=website_url,
        )
        logger.info(f"Context updated with user info: {name} ({email})")
