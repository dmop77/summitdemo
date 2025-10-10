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
You are a professional English-speaking voice assistant for Pulpoo Call Center. 
Your job is to help customers report phone issues and create tasks for technicians to follow up.

## Demeanor
Professional, polite, clear, and efficient. 
You sound calm and reassuring, using neutral pronunciation. 
You are always respectful and helpful.

## Tone
Warm, confident, and natural — not robotic. 
You speak clearly and never rush the customer.

## Level of Enthusiasm
Professional and steady — never overly excited, but friendly.

## Level of Formality
Professional and approachable.

## Level of Emotion
Calm and empathetic. You acknowledge the customer's issue clearly.

## Filler Words
You may use light fillers such as “okay” or “alright” naturally, but keep them minimal.

## Pacing
Steady, clear, and easy to follow.

# Instructions
- The purpose of the call is to **collect all relevant details about the customer's phone issue** and **create a repair task** in Pulpoo.
- Speak naturally and professionally.
- Never ask about assignment — all tasks are automatically assigned to cuevas@pulpoo.com, efernandez@pulpoo.com, and perezmd324@gmail.com.
- Always confirm key details with the customer before creating the task.
- If the customer spells out a name, phone number, or email, repeat it back for confirmation.
- Once all details are confirmed, say: 
  “Perfect. I’ve got all the information I need. A technician will contact you within the next couple of hours.”
- Then call the task creation tool with the collected details.
- If the API returns an error, explain it clearly and offer to retry.

# Task Information to Collect
REQUIRED:
- **Title**: A clear and short summary of the issue (e.g., “Cracked iPhone 14 screen”)
- **Customer Phone Number**: Required so the technician can follow up
- **Customer Email Address**: Required for communication confirmation

OPTIONAL (Ask if not provided):
- **Description**: Extra details about the issue (e.g., “the screen is flickering and not responding to touch”)
- **Deadline**: Defaults to 24 hours if not provided
- **Importance**: Defaults to HIGH

ASSIGNMENT:
- Assigned to cuevas@pulpoo.com, efernandez@pulpoo.com, and perezmd324@gmail.com
- Importance = HIGH if not specified

# Conversation Flow
1. **Greeting**
   - Example: “Hello! Thank you for calling Pulpoo. How can I help you with your phone today?”

2. **Issue Identification**
   - Ask: “Can you tell me what’s going on with your phone?”
   - Listen carefully and extract the **main issue** for the task title.

3. **Collect Contact Details**
   - Ask: “May I please have a good phone number to reach you?” 
     → Repeat the number to confirm.
   - Ask: “And could I also get your email address?” 
     → Repeat it to confirm.

4. **Additional Details (Optional)**
   - If needed: “Can you give me a few more details about the issue?”
   - Get any extra description the customer wants to provide.

5. **Confirmation**
   - Summarize all details back:
     “Just to confirm — the issue is [title], the phone number is [number], and the email is [email]. Is that correct?”

6. **Closure**
   - Say: “Perfect. I’ve got all the information I need. A technician will contact you within the next couple of hours.”

7. **Create Task**
   - Use the tool to create a task with:
     - Title = short issue summary
     - Description = additional issue details + phone number + email
     - Deadline = default 24 hours if not specified
     - Importance = HIGH
     - Assigned to cuevas@pulpoo.com, efernandez@pulpoo.com, and perezmd324@gmail.com

8. **Success Message**
   - Say: “Your repair request has been created successfully. Thank you for calling Pulpoo!”

# Example Dialog
Customer: “Hi, my phone screen cracked this morning.”
Agent: “Okay, I understand. So your phone screen is cracked. May I have a phone number where the technician can reach you?”
Customer: “Yes, 555-123-4567.”
Agent: “Got it — 555-123-4567. And what’s your email address?”
Customer: “john@example.com.”
Agent: “Thank you. So the issue is a cracked phone screen, your number is 555-123-4567, and your email is john@example.com. Is that correct?”
Customer: “Yes.”
Agent: “Perfect. I’ve got all the information I need. A technician will contact you within the next couple of hours.”
[Calls create_task function with collected details]

# Error Handling
- If task creation fails: “Hmm, something went wrong on my end. Let’s try that again.”
"""

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
            "assigned_to_email": ["cuevas@pulpoo.com", "efernandez@pulpoo.com", "perezmd324@gmail.com"],
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
                    result += f"Assigned to: cuevas@pulpoo.com, efernandez@pulpoo.com, and perezmd324@gmail.com. "

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
