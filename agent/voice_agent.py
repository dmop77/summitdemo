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
        self.conversation_history: list = []  # Track conversation for summary

    def _build_system_prompt(self) -> str:
        """Build dynamic system prompt based on context."""
        prompt = """You are a friendly appointment scheduling assistant guiding users through a natural conversation.

YOUR CONVERSATION FLOW:
1. Greet warmly with their name
2. Share interesting insight about their business (1-2 sentences, natural tone)
3. Ask an engaging follow-up question about their business or needs
4. Guide toward scheduling with interest ("This sounds great! We should schedule time to discuss this further")
5. Ask for their preferred time in a natural way
6. Once they provide time: Schedule immediately and confirm with "Perfect! See you then."

TONE & STYLE:
- Sound like a real person having a conversation, not a robot
- Be genuinely interested in their business
- Use conversational phrases like "So you work with...", "That's interesting because..."
- Ask clarifying questions to engage them
- Guide naturally toward scheduling (don't force it)

SCHEDULING RULES:
- When user mentions ANY time: Use schedule_appointment_tool immediately
- Time format: ISO "YYYY-MM-DDTHH:MM:SS" (convert relative dates to actual dates)
- After successful scheduling: Only say "Perfect! See you then." and STOP

CONVERSATION STATES:
- GREETING: Introduce yourself and their business
- CONVERSATION: Chat naturally and understand their needs  
- TIME_COLLECTION: Ask for their preferred time
- After scheduling: Say confirmation and STOP

Keep responses natural (2-4 sentences), never more than one paragraph."""

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

        # Build conversation summary from history if not provided
        if not summary and hasattr(self, 'conversation_history') and self.conversation_history:
            # Include last 4 exchanges (2 user + 2 agent messages)
            recent = self.conversation_history[-4:]
            summary = "\n".join(recent)

        result = await self.scheduler.schedule_appointment(
            user_name=self.conversation_context.user_info.name,
            user_email=self.conversation_context.user_info.email,
            appointment_topic=topic,
            preferred_date=preferred_time,
            summary_notes=summary,
        )

        if result["success"]:
            self.state = ConversationState.COMPLETED
            # Return very brief confirmation only
            return "Perfect! See you then."
        else:
            # If scheduling fails (e.g., invalid date), ask agent to retry
            # Don't change state - stay in TIME_COLLECTION
            error_msg = result.get('error', 'Unable to schedule')
            return f"Could you provide a valid future date? {error_msg}"

    async def process_message(self, user_input: str, session_id: str) -> str:
        """Process user message and return agent response.

        Args:
            user_input: User's spoken/typed message
            session_id: Conversation session ID

        Returns:
            Agent's response
        """
        # If conversation is already completed, don't process more messages
        if self.state == ConversationState.COMPLETED:
            return ""
        
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

            # Prepare the full prompt for this turn with appointment guidance
            appointment_guidance = ""
            if self.state == ConversationState.CONVERSATION:
                appointment_guidance = """
IMPORTANT: Push toward scheduling QUICKLY. Don't have a long discussion.
If user responds: Say "Great! When would you be available for a call?"
If they give a time: Use the scheduling tool immediately.
Keep everything SHORT - 1-2 sentences max per response."""
            
            turn_prompt = f"""{context_info}

{state_guidance}

{appointment_guidance}

User message: {user_input}

CRITICAL RULES:
- Keep response to 1-2 sentences MAXIMUM
- DON'T start with "Hi [name]" - only use that in initial greeting
- Be conversational and natural, not scripted
- If they mention a time: Extract it and use the scheduling tool
- If they ask questions: Answer briefly then ask for time
- Focus on getting a specific time for the appointment"""

            # Run the agent
            result = await self.agent.run(turn_prompt)
            # Extract output from AgentRunResult object
            response_text = result.output if hasattr(result, 'output') else str(result)

            logger.info(f"Agent response: {response_text}")
            
            # Track conversation history for summary
            self.conversation_history.append(f"User: {user_input}")
            self.conversation_history.append(f"Agent: {response_text}")

            # Update state based on conversation flow and trigger smart prompting
            user_lower = user_input.lower()
            
            # Detect if user is ready for scheduling
            scheduling_keywords = ["when", "time", "schedule", "book", "appointment", 
                                 "available", "tomorrow", "next", "monday", "tuesday", 
                                 "wednesday", "thursday", "friday", "saturday", "sunday",
                                 "today", "week", "month", "afternoon", "morning", "evening",
                                 "am", "pm", "o'clock", "oclock", "pm", "noon", "midnight"]
            
            if any(word in user_lower for word in scheduling_keywords) and self.state != ConversationState.TIME_COLLECTION:
                self.state = ConversationState.TIME_COLLECTION
            elif self.state == ConversationState.GREETING:
                # After greeting, move to conversation
                self.state = ConversationState.CONVERSATION

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
            # Handle both string and ScrapedContent object
            if hasattr(user, 'website_summary'):
                if isinstance(user.website_summary, str):
                    website_summary = user.website_summary
                else:
                    # If it's a ScrapedContent object, get the summary field
                    website_summary = user.website_summary.summary if hasattr(user.website_summary, 'summary') else str(user.website_summary)
            else:
                website_summary = 'Not available'
            
            greeting_prompt = f"""Generate EXACTLY this format (fill in brackets):
"Hi {user.name}! I see you're interested in [SERVICE]. From what I understand, [BRIEF INSIGHT]. Would you like to talk about it further over a call?"

Summary: {website_summary}

Just fill in the brackets naturally. Keep it short."""

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
