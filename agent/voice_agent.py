"""
Context-aware voice agent for appointment scheduling.

This agent manages the entire conversation:
1. Greets the user with their name
2. Acknowledges their website/business
3. Briefly chats about their needs
4. Suggests an appointment
5. Collects their preferred time
6. Creates the appointment via Pulpoo
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel

from config import get_voice_config, get_agent_config
from schemas import ConversationContext, UserInfo
from agent_tools import AppointmentScheduler

logger = logging.getLogger(__name__)


class ConversationState:
    """Track conversation state for the agent."""

    GREETING = "greeting"
    CONVERSATION = "conversation"
    APPOINTMENT_PROPOSAL = "appointment_proposal"
    TIME_COLLECTION = "time_collection"
    SCHEDULING = "scheduling"
    COMPLETED = "completed"


class BackgroundAgent:
    """Context-aware agent managing the entire conversation."""

    def __init__(self):
        """Initialize the background agent."""
        self.voice_config = get_voice_config()
        self.agent_config = get_agent_config()

        # Initialize appointment scheduler
        self.scheduler = AppointmentScheduler(
            openai_api_key=self.voice_config.openai_api_key,
            pulpoo_api_key=self.voice_config.pulpoo_api_key,
        )

        # Create Pydantic AI agent
        model = OpenAIChatModel(model_name=self.voice_config.openai_model)
        self.agent = Agent(
            model=model,
            tools=[self._schedule_appointment_tool],
            system_prompt=self._build_system_prompt(),
        )

        self.conversation_context: Optional[ConversationContext] = None
        self.state = ConversationState.GREETING

    def _build_system_prompt(self) -> str:
        """Build dynamic system prompt based on context."""
        prompt = """You are a friendly appointment scheduling assistant.

Your goal is to help the user schedule a consultation or meeting.

KEY INSTRUCTIONS:
1. When the user mentions a time (e.g., "tomorrow at 2pm", "next Monday at 10am"), schedule the appointment immediately using the schedule_appointment_tool
2. Extract the time clearly and use ISO format (e.g., "2025-11-15T14:00:00")
3. Keep responses short and natural (1-3 sentences max)
4. Be conversational, not robotic
5. Once appointment is scheduled, confirm it to the user

IMPORTANT:
- Don't ask for name/email again - you already have it
- When user provides a time, schedule it immediately
- Interpret casual time references (tomorrow, next week, etc.) relative to today
- Always convert to ISO datetime format for scheduling"""

        return prompt

    async def _schedule_appointment_tool(
        self,
        ctx: RunContext,
        topic: str,
        preferred_time: str,
        summary: str = "",
    ) -> str:
        """Tool for scheduling appointments.

        Args:
            ctx: Run context
            topic: What the appointment is about
            preferred_time: Time in ISO format (e.g., "2025-11-15T14:30:00")
            summary: Brief summary of the conversation

        Returns:
            Confirmation message
        """
        if not self.conversation_context or not self.conversation_context.user_info:
            return "Error: User information not available"

        result = await self.scheduler.schedule_appointment(
            user_name=self.conversation_context.user_info.name,
            user_email=self.conversation_context.user_info.email,
            appointment_topic=topic,
            preferred_date=preferred_time,
            summary_notes=summary,
        )

        if result["success"]:
            self.state = ConversationState.COMPLETED
            return result["message"]
        else:
            return f"Sorry, I couldn't schedule the appointment: {result['error']}"

    async def process_message(self, user_input: str, session_id: str) -> str:
        """Process user message and return agent response.

        Args:
            user_input: User's spoken/typed message
            session_id: Conversation session ID

        Returns:
            Agent's response
        """
        try:
            # Initialize context if needed
            if self.conversation_context is None:
                self.conversation_context = ConversationContext(session_id=session_id)

            # Build context-aware prompt
            context_info = ""
            if self.conversation_context.user_info:
                user = self.conversation_context.user_info
                context_info = f"""
CONTEXT (known to you, don't ask for it):
- User name: {user.name}
- User email: {user.email}
- Website: {user.website_url}
- Website summary: {user.website_summary if hasattr(user, 'website_summary') else 'Not available'}
"""

            # Add state-specific guidance
            state_guidance = ""
            if self.state == ConversationState.TIME_COLLECTION:
                state_guidance = """
The user has agreed to schedule. Now extract their preferred time from their message.
If they give a time, schedule the appointment immediately.
If unclear, ask for clarification."""

            # Prepare the full prompt for this turn
            turn_prompt = f"""{context_info}

{state_guidance}

User message: {user_input}

Respond naturally and helpfully. Keep it brief."""

            # Run the agent
            result = await self.agent.run(turn_prompt)
            # Extract output from AgentRunResult object
            response_text = result.output if hasattr(result, 'output') else str(result)

            logger.info(f"Agent response: {response_text}")

            # Update state based on conversation flow
            if "schedule" in user_input.lower() or "time" in user_input.lower():
                self.state = ConversationState.TIME_COLLECTION

            return response_text

        except Exception as e:
            logger.error(f"Error in agent: {e}", exc_info=True)
            return "I encountered an error. Could you please repeat that?"

    async def get_greeting(self) -> str:
        """Generate a greeting message for the user.

        Returns:
            Greeting message
        """
        try:
            if not self.conversation_context or not self.conversation_context.user_info:
                return "Hi there! I'm ready to help you schedule an appointment."

            user = self.conversation_context.user_info
            website_summary = user.website_summary if hasattr(user, 'website_summary') else 'Not available'
            greeting_prompt = f"""Generate a brief greeting message in this exact format:

Hello {user.name}, {website_summary}. Want to talk into it further? Let's schedule an appointment.

Guidelines:
- Start with "Hello [name],"
- Include a brief 1 sentence summary of the website/business
- End with "Want to talk into it further? Let's schedule an appointment."
- Keep it natural and concise
- One sentence for the website summary"""

            result = await self.agent.run(greeting_prompt)
            # Extract output from AgentRunResult object
            greeting_text = result.output if hasattr(result, 'output') else str(result)
            greeting_text = greeting_text.strip()
            logger.info(f"Generated greeting: {greeting_text}")
            return greeting_text

        except Exception as e:
            logger.error(f"Error generating greeting: {e}", exc_info=True)
            # Fallback greeting if agent fails
            user_name = self.conversation_context.user_info.name if self.conversation_context and self.conversation_context.user_info else "there"
            return f"Hi {user_name}! Thanks for joining. Let's discuss scheduling an appointment."

    def set_user_info(self, name: str, email: str, website_url: str, website_summary: str = ""):
        """Set user information from setup phase.

        Args:
            name: User's name
            email: User's email
            website_url: User's website URL
            website_summary: Summary of website content
        """
        if self.conversation_context is None:
            self.conversation_context = ConversationContext(session_id="temp")

        self.conversation_context.user_info = UserInfo(
            name=name,
            email=email,
            website_url=website_url,
        )

        # Store summary if provided
        if website_summary:
            self.conversation_context.user_info.website_summary = website_summary

        logger.info(f"Agent context set: {name} ({email})")

    def reset(self):
        """Reset agent for new conversation."""
        self.conversation_context = None
        self.state = ConversationState.GREETING
        logger.info("Agent reset")

    async def initialize(self):
        """Initialize the agent (compatibility method)."""
        pass

    async def cleanup(self):
        """Cleanup agent resources and reset state."""
        self.reset()

    def reset_conversation(self):
        """Reset conversation (compatibility method)."""
        self.reset()

    def update_context_with_scraped_content(self, content: str):
        """Update context with scraped website content (compatibility method).
        
        Args:
            content: Scraped website content/summary
        """
        if self.conversation_context and self.conversation_context.user_info:
            self.conversation_context.user_info.website_summary = content
