"""
Task Creation Voice Agent - OpenAI Realtime API
===============================================
Voice agent that creates tasks via API using OpenAI Realtime API.
Implements speech-to-speech architecture for natural conversation.
"""

import asyncio
import json
import logging
import os
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import aiohttp
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables
load_dotenv(".env")

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Configuration
PULPOO_API_KEY = os.getenv("PULPOO_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class TaskCreationVoiceAgent:
    """Voice assistant that creates tasks through conversational interface using OpenAI Realtime API."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.http_session = None
        self.session = None
        
        # Agent configuration
        self.agent_instructions = """# Personality and Tone
## Identity
You are a professional task management assistant for Pulpoo, helping users create tasks efficiently through voice conversation.

## Task
You help users create tasks in Pulpoo by capturing task information through natural, friendly conversation.

## Demeanor
Professional, helpful, and efficient. You're focused on getting the task details right.

## Tone
Warm and conversational, but concise. You don't over-explain.

## Level of Enthusiasm
Calm and measured - professional but friendly.

## Level of Formality
Professional but approachable.

## Level of Emotion
Matter-of-fact but empathetic when needed.

## Filler Words
Occasionally - use "um" or "uh" sparingly to sound natural.

## Pacing
Normal conversational pace, not rushed.

# Instructions
- If a user provides a name, phone number, or something where you need to know the exact spelling, always repeat it back to the user to confirm you have the right understanding before proceeding.
- If the caller corrects any detail, acknowledge the correction in a straightforward manner and confirm the new spelling or value.
- Keep responses natural and conversational
- Don't ask for assignment information (automatically assigned to cuevas@pulpoo.com)
- For deadlines, get specific dates/times (e.g., "January 15th at 2 PM")
- Importance defaults to HIGH if not specified
- Confirm details by reading them back before creating
- If API returns an error, explain it clearly and offer to retry

# Task Information to Collect

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

EXAMPLES:

User: "Create a task to review the Q4 report"
You: "I'll help you create that task in Pulpoo. When do you need the Q4 report reviewed by?"

User: "By next Friday at 5 PM"
You: "Got it. How important is this task - low, medium, or high priority?"

User: "High priority"
You: "Perfect. Let me confirm: I'll create a high priority task titled 'Review Q4 report', due next Friday at 5 PM, assigned to cuevas@pulpoo.com. Is that correct?"

User: "Yes"
You: [Calls create_task function]"""

    async def create_task_tool(self, title: str, description: Optional[str] = None, 
                              deadline: Optional[str] = None, importance: str = "HIGH") -> str:
        """Create a new task in Pulpoo via the API."""
        
        # Validate importance
        if importance.upper() not in ["LOW", "MEDIUM", "HIGH"]:
            importance = "HIGH"
        else:
            importance = importance.upper()

        # Build payload for Pulpoo API
        payload = {
            "title": title,
            "description": description or f"Task created via voice agent: {title}",
            "assigned_to_email": "cuevas@pulpoo.com",
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
        import pytz
        
        deadline = datetime.now(pytz.UTC) + timedelta(hours=24)
        return deadline.strftime("%Y-%m-%dT%H:%M:%SZ")

    async def get_current_date_time(self) -> str:
        """Get the current date and time for deadline calculations."""
        current_datetime = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        return f"The current date and time is {current_datetime}"

    async def start_session(self):
        """Start a new Realtime API session."""
        try:
            # Create the session
            self.session = await self.client.beta.realtime.sessions.create(
                model="gpt-4o-realtime-preview",
                voice="alloy",
                instructions=self.agent_instructions,
                input_audio_format="pcm16",
                output_audio_format="pcm16",
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "create_task",
                            "description": "Create a new task in Pulpoo via the API",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "title": {
                                        "type": "string",
                                        "description": "Task title (required)"
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Detailed description of the task"
                                    },
                                    "deadline": {
                                        "type": "string",
                                        "description": "Deadline in ISO 8601 format (e.g., '2025-01-15T17:00:00Z')"
                                    },
                                    "importance": {
                                        "type": "string",
                                        "enum": ["LOW", "MEDIUM", "HIGH"],
                                        "description": "Task importance - defaults to HIGH for Pulpoo"
                                    }
                                },
                                "required": ["title"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_current_date_time",
                            "description": "Get the current date and time for deadline calculations",
                            "parameters": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    }
                ]
            )
            
            logger.info(f"Created Realtime session: {self.session.id}")
            return self.session
            
        except Exception as e:
            logger.error(f"Failed to create Realtime session: {e}")
            raise

    async def handle_tool_call(self, tool_call):
        """Handle function tool calls from the agent."""
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        logger.info(f"Handling tool call: {function_name} with args: {arguments}")
        
        try:
            if function_name == "create_task":
                result = await self.create_task_tool(
                    title=arguments.get("title"),
                    description=arguments.get("description"),
                    deadline=arguments.get("deadline"),
                    importance=arguments.get("importance", "HIGH")
                )
            elif function_name == "get_current_date_time":
                result = await self.get_current_date_time()
            else:
                result = f"Unknown function: {function_name}"
                
            return result
            
        except Exception as e:
            logger.error(f"Error handling tool call {function_name}: {e}")
            return f"Error executing {function_name}: {str(e)}"

    async def process_audio_stream(self, audio_stream):
        """Process incoming audio stream and handle responses."""
        if not self.session:
            await self.start_session()
            
        # This would be implemented with WebSocket connection to the Realtime API
        # For now, this is a placeholder for the actual implementation
        pass

    async def cleanup(self):
        """Cleanup resources."""
        if self.http_session:
            await self.http_session.close()
        if self.session:
            try:
                await self.client.beta.realtime.sessions.delete(self.session.id)
            except Exception as e:
                logger.error(f"Error deleting session: {e}")


async def main():
    """Main entry point for the voice agent."""
    
    # Validate configuration
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY must be set in environment")
        return
    if not PULPOO_API_KEY:
        logger.error("PULPOO_API_KEY must be set in environment")
        return

    agent = TaskCreationVoiceAgent()
    
    try:
        # Start the session
        session = await agent.start_session()
        logger.info(f"Voice agent started with session: {session.id}")
        
        # Keep the agent running
        print("Voice agent is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down voice agent...")
    except Exception as e:
        logger.error(f"Error running voice agent: {e}")
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
