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
from agent_tools import AppointmentScheduler, parse_appointment_time
from db_client import SupabaseClient

logger = logging.getLogger(__name__)


class ConversationState:
    """Track conversation state for the agent."""

    GREETING = "greeting"
    ENGAGEMENT = "engagement"  # User is asking questions - answer them and keep proposing appointment
    TIME_COLLECTION = "time_collection"  # User agreed to appointment - collect preferred time
    COMPLETED = "completed"


class BackgroundAgent:
    """Context-aware agent managing the entire conversation."""

    def __init__(self):
        """Initialize the background agent."""
        self.voice_config = get_voice_config()
        self.agent_config = get_agent_config()

        # Initialize conversation context first (before building system prompt)
        self.conversation_context: Optional[ConversationContext] = None
        self.state = ConversationState.GREETING
        self.conversation_history: list = []  # Track conversation for summary
        self._context_cache = {}  # Cache built context to avoid rebuilding

        # Initialize appointment scheduler
        self.scheduler = AppointmentScheduler(
            openai_api_key=self.voice_config.openai_api_key,
            pulpoo_api_key=self.voice_config.pulpoo_api_key,
        )

        # Create Pydantic AI agent (now conversation_context is initialized)
        model = OpenAIChatModel(model_name=self.voice_config.openai_model)
        self.agent = Agent(
            model=model,
            tools=[self._schedule_appointment_tool],
            system_prompt=self._build_system_prompt(),
        )

    def _build_system_prompt(self) -> str:
        """Build system prompt with user context for the conversation.

        This is called once at initialization and includes user context
        so the agent remembers who they're talking to throughout the conversation.
        """
        prompt = """You are a friendly business consultant helping schedule appointments.

GOAL: Help the user schedule an appointment to discuss their business needs in detail.

CONVERSATION FLOW:
1. [GREETING DONE]: The greeting + scraped website overview has already been sent
2. [USER ENGAGEMENT]: User responds with questions about what was scraped
   - Answer their question briefly (1-2 sentences)
   - Be knowledgeable about what you learned from their website
3. [ALWAYS PROPOSE APPOINTMENT]: After every answer, propose scheduling
   - Examples: "This is interesting! I'd love to dive deeper. Are you free next week?"
   - Or: "That makes sense. Shall we set up a call to explore this further?"
4. [ANSWER MORE QUESTIONS]: If they ask more questions, answer them and propose again
   - Keep doing this until they agree to schedule
5. [COLLECT TIME]: When they agree to appointment, ask for preferred date/time
   - Accept natural language times like "tomorrow at 2pm", "next Monday at 3pm", "next week"
6. [SCHEDULE]: Call schedule_appointment_tool with their exact time (as spoken)
   - Pass the time exactly as user said it - system will parse it
   - Examples: "tomorrow at 2 PM", "next week Monday at 3 PM", "2025-11-15T14:30:00"
7. [CLOSE]: Say ONLY "Perfect! See you then." and STOP

CRITICAL RULES:
- You already have: user name, email, website info (NEVER ask again)
- Be ready to answer unlimited questions about their business
- After each answer, always propose scheduling in a natural way
- When user agrees (says "yes", "sure", "sounds good", or provides a time), move to time collection
- When user provides time, call schedule_appointment_tool with EXACTLY what they said
- The system auto-parses times like "tomorrow at 2pm", "next week", "Monday at 3 PM", etc.
- After scheduling, say ONLY "Perfect! See you then."

TONE: Warm, professional, curious, genuinely interested in their business.

APPOINTMENT FOCUS: Answer their questions freely, but always guide back to scheduling the call."""

        # Inject user context
        if self.conversation_context and self.conversation_context.user_info:
            user = self.conversation_context.user_info
            website_summary = ""
            if hasattr(user, 'website_summary') and user.website_summary:
                website_summary = f"\n\nWhat we learned about their business:\n{user.website_summary[:400]}"  # First 400 chars

            context = f"""

USER INFORMATION (KNOWN FACTS):
- Name: {user.name}
- Email: {user.email}
- Website: {user.website_url}{website_summary}

NEVER ask for name or email again. Use this information to provide personalized, relevant responses."""
            prompt += context

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
            preferred_time: Time (can be ISO format or natural language like "tomorrow at 2pm")
            summary: Brief summary of the conversation

        Returns:
            Confirmation message
        """
        if not self.conversation_context or not self.conversation_context.user_info:
            return "Error: User information not available"

        # Parse the time - handle natural language or ISO format
        parsed_time = parse_appointment_time(preferred_time)
        if not parsed_time:
            logger.warning(f"Failed to parse appointment time: {preferred_time}")
            return f"I couldn't understand that time: '{preferred_time}'. Please say something like 'tomorrow at 2pm' or 'next Monday at 3 PM'"

        logger.info(f"Parsed appointment time: {preferred_time} → {parsed_time}")

        # Build conversation summary from history if not provided
        if not summary and hasattr(self, 'conversation_history') and self.conversation_history:
            # Include last 4 exchanges (2 user + 2 agent messages)
            recent = self.conversation_history[-4:]
            summary = "\n".join(recent)

        result = await self.scheduler.schedule_appointment(
            user_name=self.conversation_context.user_info.name,
            user_email=self.conversation_context.user_info.email,
            appointment_topic=topic,
            preferred_date=parsed_time,
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
            logger.warning(f"Failed to schedule appointment: {error_msg}")
            return f"I had trouble booking that time. {error_msg}. Could you try a different time?"

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

            # Build turn prompt with conversation history for context
            # This ensures the agent remembers what was said before
            history_str = ""
            if self.conversation_history:
                # Include last 4 messages (2 exchanges) for context
                history_str = "\n".join(self.conversation_history[-4:])
                history_str = f"Recent conversation:\n{history_str}\n\n"

            turn_prompt = f"{history_str}User message: {user_input}"

            # Run the agent with context
            result = await self.agent.run(turn_prompt)
            # Extract output from AgentRunResult object
            response_text = result.output if hasattr(result, 'output') else str(result)

            logger.info(f"Agent response: {response_text}")

            # Track conversation history for summary (minimal - just last exchange)
            self.conversation_history.append(f"User: {user_input}")
            self.conversation_history.append(f"Agent: {response_text}")
            # Keep only last 6 messages to reduce memory
            if len(self.conversation_history) > 6:
                self.conversation_history = self.conversation_history[-6:]

            # Update state based on conversation flow
            user_lower = user_input.lower()

            # Move from greeting to engagement on first user message
            if self.state == ConversationState.GREETING:
                self.state = ConversationState.ENGAGEMENT
                logger.info("✓ User engaged - in conversation mode. Answer questions and propose appointment.")

            # Detect if user is agreeing to appointment or providing time
            agreement_keywords = ["yes", "yeah", "sure", "sounds good", "ok", "okay", "agree", "absolutely",
                                "definitely", "works for me", "perfect", "let's do it", "let's schedule"]

            scheduling_keywords = ["when", "time", "schedule", "book", "appointment",
                                 "available", "tomorrow", "next", "monday", "tuesday",
                                 "wednesday", "thursday", "friday", "saturday", "sunday",
                                 "today", "week", "month", "afternoon", "morning", "evening",
                                 "am", "pm", "o'clock", "oclock", "noon", "midnight"]

            # If user agrees to appointment or provides a time while in engagement
            if self.state == ConversationState.ENGAGEMENT:
                if any(word in user_lower for word in agreement_keywords) or any(word in user_lower for word in scheduling_keywords):
                    self.state = ConversationState.TIME_COLLECTION
                    logger.info("✓ User agreed to appointment - now collecting time preference")

            return response_text

        except Exception as e:
            logger.error(f"Error in agent: {e}", exc_info=True)
            return "I encountered an error. Could you please repeat that?"

    def get_greeting(self) -> str:
        """Generate a fast, engaging greeting that starts the conversation.

        Returns:
            Greeting message
        """
        try:
            if not self.conversation_context or not self.conversation_context.user_info:
                return "Hi there! Thanks for joining. What brings you here today?"

            user = self.conversation_context.user_info

            # Extract website domain for context
            website_domain = user.website_url.replace("https://", "").replace("http://", "").split("/")[0] if user.website_url else "your business"

            # More engaging greeting that invites conversation
            greeting = f"Hi {user.name}! I see you're interested in {website_domain}. Tell me, what brought you here today and what are you looking to accomplish?"

            logger.info(f"Generated greeting: {greeting}")
            return greeting

        except Exception as e:
            logger.error(f"Error generating greeting: {e}", exc_info=True)
            # Fallback greeting if anything fails
            user_name = self.conversation_context.user_info.name if self.conversation_context and self.conversation_context.user_info else "there"
            return f"Hi {user_name}! Thanks for joining. What brought you here today?"

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
