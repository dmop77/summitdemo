"""
Voice Agent using Pydantic AI with Deepgram STT and OpenAI LLM.

Features:
- Deepgram speech-to-text (primary) with OpenAI fallback
- OpenAI GPT-4o-mini for intelligent responses
- Optional Cartesia TTS or OpenAI TTS
- Function calling for task creation via Pulpoo
- Real-time audio streaming
"""

import asyncio
import json
import logging
from typing import Optional
from datetime import datetime, timedelta

import aiohttp
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from config import get_voice_config, get_agent_config
from schemas import VoiceAgentMessage, ConversationContext, UserInfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceAssistant:
    """Main voice agent using Pydantic AI."""

    def __init__(self):
        """Initialize the voice assistant."""
        self.voice_config = get_voice_config()
        self.agent_config = get_agent_config()
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.agent = self._create_agent()
        self.conversation_context: Optional[ConversationContext] = None

    def _create_agent(self) -> Agent:
        """Create the Pydantic AI agent with tools."""
        # Initialize the OpenAI model
        model = OpenAIModel(
            model_name=self.voice_config.openai_model,
            api_key=self.voice_config.openai_api_key,
        )

        # Create agent with instructions
        agent = Agent(
            model=model,
            instructions=self.agent_config.system_prompt,
            deps_type=RunContext,
        )

        # Register tools
        agent.on_call = self._on_agent_call

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

            # Get agent response
            response = await self.agent.arun(
                user_input,
                deps=RunContext(deps={"session_id": session_id, "context": self.conversation_context}),
            )

            # Add agent message to history
            agent_msg = VoiceAgentMessage(
                message_id=f"msg_{len(self.conversation_context.conversation_history)}",
                session_id=session_id,
                speaker="agent",
                text=response.data,
            )
            self.conversation_context.conversation_history.append(agent_msg)

            return response.data

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return "I encountered an error processing your request. Could you please repeat that?"

    async def create_task(
        self,
        title: str,
        description: str,
        customer_email: str,
    ) -> bool:
        """
        Create a support task in Pulpoo.

        Args:
            title: Task title
            description: Task description
            customer_email: Customer's email address

        Returns:
            True if successful, False otherwise
        """
        if not self.voice_config.pulpoo_api_key:
            logger.warning("Pulpoo API key not configured")
            return False

        try:
            headers = {
                "X-API-Key": self.voice_config.pulpoo_api_key,
                "Content-Type": "application/json",
            }

            payload = {
                "title": title,
                "description": description,
                "assigned_to_email": "support@pulpoo.com",
                "importance": "HIGH",
                "canal": "Voice Assistant",
                "deadline": (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z",
            }

            if not self.http_session:
                logger.error("HTTP session not initialized")
                return False

            async with self.http_session.post(
                self.voice_config.pulpoo_api_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status in [200, 201]:
                    logger.info(f"Task created: {title}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create task: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Error creating task: {e}", exc_info=True)
            return False

    async def _on_agent_call(self, call_context: RunContext):
        """Handle function calls from the agent."""
        # This is called when the agent uses tools
        # Implementation depends on what tools you want to expose
        pass
