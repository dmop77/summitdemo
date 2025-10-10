"""
Task Creation Voice Agent - Local Development
==============================================
Voice agent that creates tasks via API using OpenAI Realtime API.
Runs locally and serves a web interface.
"""

from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import Agent, AgentSession, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import openai
from datetime import datetime
from typing import Optional
import os
import aiohttp
import logging

# Load environment variables
load_dotenv(".env")

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Configuration
PULPOO_API_KEY = os.getenv("PULPOO_API_KEY")


class TaskCreationAssistant(Agent):
    """Voice assistant that creates tasks through conversational interface."""

    def __init__(self):
        super().__init__(
            instructions="""You are a professional task management assistant for Pulpoo, helping users create tasks efficiently through voice conversation.

YOUR ROLE:
- Capture task information through natural, friendly conversation
- Ask clarifying questions when details are unclear or missing
- Confirm all details before creating the task in Pulpoo
- Be concise but thorough - don't over-explain

TASK INFORMATION TO COLLECT:

REQUIRED:
- Title: A clear, descriptive task title (REQUIRED)

OPTIONAL (Ask if relevant to the task):
- Description: Additional details about the task
- Deadline: When it needs to be completed (get specific date and time)
- Importance: How urgent is it (LOW, MEDIUM, or HIGH) - defaults to HIGH

IMPORTANT NOTES:
- All tasks are automatically assigned to cuevas@pulpoo.com (no need to ask for assignment)
- If no deadline is provided, tasks are set to 24 hours from now
- Importance defaults to HIGH for Pulpoo tasks

CONVERSATION FLOW:
1. Listen to what the user wants to create
2. Extract the core task title first
3. Ask follow-up questions for important missing details (description, deadline, importance)
4. Confirm all details before creating
5. Call create_task function with collected information
6. Inform user of success or any errors

IMPORTANT GUIDELINES:
- Keep responses natural and conversational
- Don't ask for assignment information (automatically assigned to cuevas@pulpoo.com)
- For deadlines, get specific dates/times (e.g., "January 15th at 2 PM")
- Importance defaults to HIGH if not specified
- Confirm details by reading them back before creating
- If API returns an error, explain it clearly and offer to retry

EXAMPLES:

User: "Create a task to review the Q4 report"
You: "I'll help you create that task in Pulpoo. When do you need the Q4 report reviewed by?"

User: "By next Friday at 5 PM"
You: "Got it. How important is this task - low, medium, or high priority?"

User: "High priority"
You: "Perfect. Let me confirm: I'll create a high priority task titled 'Review Q4 report', due next Friday at 5 PM, assigned to cuevas@pulpoo.com. Is that correct?"

User: "Yes"
You: [Calls create_task function]
"""
        )
        self.http_session = None

    @function_tool
    async def create_task(
        self,
        context: RunContext,
        title: str,
        description: Optional[str] = None,
        deadline: Optional[str] = None,
        importance: str = "HIGH",
    ) -> str:
        """Create a new task in Pulpoo via the API.

        Args:
            title: Task title (required)
            description: Detailed description of the task
            deadline: Deadline in ISO 8601 format (e.g., '2025-01-15T17:00:00Z')
            importance: Task importance (LOW, MEDIUM, or HIGH) - defaults to HIGH for Pulpoo
        """

        # Validate importance
        if importance.upper() not in ["LOW", "MEDIUM", "HIGH"]:
            importance = "HIGH"
        else:
            importance = importance.upper()

        # Build payload for Pulpoo API
        payload = {
            "title": title,
            "description": description or f"Task created via voice agent: {title}",
            "assigned_to_email": "cuevas@pulpoo.com",  # Fixed assignment as per your API
            "deadline": deadline or self._get_default_deadline(),
            "importance": importance,
        }

        logger.info(f"Creating task in Pulpoo: {payload}")

        try:
            if not self.http_session:
                self.http_session = aiohttp.ClientSession()

            headers = {
                "X-API-Key": PULPOO_API_KEY,
                "Content-Type": "application/json",
            }

            async with self.http_session.post(
                "https://api.pulpoo.com/v1/external/tasks/create", 
                json=payload, 
                headers=headers, 
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_data = await response.json()

                if response.status == 200 or response.status == 201:
                    # Build success message
                    result = f"Task created successfully in Pulpoo! "
                    result += f"Title: {title}. "
                    result += f"Assigned to: cuevas@pulpoo.com. "

                    if deadline:
                        result += f"Deadline: {deadline}. "

                    result += f"Importance: {importance}."

                    logger.info(f"Task created successfully in Pulpoo: {title}")
                    return result

                else:
                    error_msg = response_data.get("error", "Unknown error")
                    logger.error(f"Pulpoo API error {response.status}: {error_msg}")

                    # Provide user-friendly error messages
                    if "not found" in error_msg.lower():
                        return "I couldn't create the task because the assigned user wasn't found. Please check the email address and try again."
                    elif "invalid input" in error_msg.lower():
                        return f"There was an issue with the task details: {error_msg}. Please verify the information and try again."
                    else:
                        return f"I encountered an error creating the task: {error_msg}. Would you like to try again?"

        except aiohttp.ClientError as e:
            logger.error(f"Network error: {str(e)}")
            return "I'm having trouble connecting to Pulpoo. Please check your connection and try again."
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return f"An unexpected error occurred: {str(e)}. Please try again."

    def _get_default_deadline(self) -> str:
        """Get a default deadline 24 hours from now in ISO format."""
        from datetime import datetime, timedelta
        import pytz
        
        # Create deadline 24 hours from now in UTC
        deadline = datetime.now(pytz.UTC) + timedelta(hours=24)
        return deadline.strftime("%Y-%m-%dT%H:%M:%SZ")

    @function_tool
    async def get_current_date_time(self, context: RunContext) -> str:
        """Get the current date and time for deadline calculations."""
        current_datetime = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        return f"The current date and time is {current_datetime}"

    async def on_enter(self):
        """Called when agent becomes active."""
        await self.session.generate_reply(
            instructions="Greet the user warmly and ask what task they'd like to create."
        )

    async def on_exit(self):
        """Cleanup when agent exits."""
        if self.http_session:
            await self.http_session.close()


async def entrypoint(ctx: agents.JobContext):
    """Entry point for the agent."""

    # Validate configuration
    if not PULPOO_API_KEY:
        logger.error("PULPOO_API_KEY must be set in environment")
        return

    # Configure session with OpenAI Realtime API (handles STT, LLM, and TTS)
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="alloy",  # Options: alloy, echo, shimmer
            temperature=0.7,
            instructions="",  # Instructions are in the Agent class
            modalities=["audio", "text"],
            turn_detection=openai.realtime.ServerVadOptions(
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=500,
            ),
        )
    )

    # Start the session
    await session.start(room=ctx.room, agent=TaskCreationAssistant())


if __name__ == "__main__":
    # Validate environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment")
        exit(1)
    if not PULPOO_API_KEY:
        print("❌ PULPOO_API_KEY not found in environment")
        exit(1)

    # Run the agent
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))