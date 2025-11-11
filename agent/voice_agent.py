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
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart

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
        self.agent = None  # Will be created with context-aware prompt
        self.conversation_context: Optional[ConversationContext] = None
        self.dynamic_system_prompt: Optional[str] = None
        self.message_history: list[ModelMessage] = []  # Track Pydantic AI message history

    def _create_agent(self, system_prompt: Optional[str] = None) -> Agent:
        """
        Create the Pydantic AI agent with tools and system prompt.

        Args:
            system_prompt: Custom system prompt (uses dynamic prompt if provided)

        Returns:
            Configured Agent instance
        """
        # Initialize the OpenAI model with ModelSettings for temperature
        model = OpenAIChatModel(
            model_name=self.voice_config.openai_model,
            settings=ModelSettings(temperature=0.7),
        )

        # Use provided system prompt or fall back to default
        prompt = system_prompt or self.agent_config.system_prompt

        # Create agent with system instructions
        agent = Agent(
            model=model,
            system_prompt=prompt,
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

    def reset_conversation(self):
        """Reset conversation history for a fresh session."""
        self.message_history = []
        if self.conversation_context:
            self.conversation_context.conversation_history = []
        logger.info("Conversation history reset")

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

            # Get agent response with conversation history
            response = await self.agent.run(user_input, message_history=self.message_history)

            # Extract text from response - Pydantic AI v2 uses response.output
            response_text = str(response.output) if hasattr(response, 'output') else str(response)
            logger.info(f"Agent response: {response_text}")

            # Update message history with the new exchange
            self.message_history = response.new_messages()

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
        Update conversation context with user information and rebuild agent with dynamic prompt.

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

        # Build dynamic system prompt with user context
        website_info = f"Website URL: {website_url}"
        self.dynamic_system_prompt = self.agent_config.build_dynamic_prompt(
            self.agent_config.system_prompt,
            user_name=name,
            user_email=email,
            website_info=website_info
        )

        # Recreate agent with dynamic prompt
        self.agent = self._create_agent(system_prompt=self.dynamic_system_prompt)

        logger.info(f"Context updated with user info: {name} ({email})")

    def update_context_with_scraped_content(self, scraped_content):
        """
        Update conversation context with scraped website content and rebuild agent prompt.

        Args:
            scraped_content: ScrapedContent object with website information
        """
        if self.conversation_context is None:
            import uuid
            self.conversation_context = ConversationContext(session_id=str(uuid.uuid4()))

        self.conversation_context.scraped_content = scraped_content

        # Rebuild dynamic prompt with scraped content
        if self.conversation_context.user_info:
            website_info = self._format_website_info(scraped_content)
            self.dynamic_system_prompt = self.agent_config.build_dynamic_prompt(
                self.agent_config.system_prompt,
                user_name=self.conversation_context.user_info.name,
                user_email=self.conversation_context.user_info.email,
                website_info=website_info
            )

            # Recreate agent with updated prompt
            self.agent = self._create_agent(system_prompt=self.dynamic_system_prompt)

        logger.info(f"Context updated with scraped content from: {scraped_content.url}")

    @staticmethod
    def _format_website_info(scraped_content) -> str:
        """
        Format scraped content into readable website information.

        Args:
            scraped_content: ScrapedContent object

        Returns:
            Formatted website information string
        """
        info = f"Website Title: {scraped_content.title}\n"
        info += f"Website URL: {scraped_content.url}\n"

        if scraped_content.summary:
            info += f"Website Summary: {scraped_content.summary}\n"

        if scraped_content.content:
            # Limit content to first 500 characters to keep prompt manageable
            content_preview = scraped_content.content[:500]
            if len(scraped_content.content) > 500:
                content_preview += "..."
            info += f"Website Content (preview): {content_preview}\n"

        if scraped_content.pages_crawled:
            info += f"Pages Crawled: {scraped_content.pages_crawled}\n"

        return info
