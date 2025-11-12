"""
Simplified agent tools for appointment scheduling.

Tools:
- schedule_appointment: Create appointment in Pulpoo with user details and summary
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

import aiohttp
from config import get_voice_config

logger = logging.getLogger(__name__)


class AppointmentScheduler:
    """Simplified appointment scheduling tool."""

    def __init__(self, openai_api_key: str, pulpoo_api_key: str):
        """
        Initialize scheduler.

        Args:
            openai_api_key: OpenAI API key (for context)
            pulpoo_api_key: Pulpoo API key
        """
        self.openai_api_key = openai_api_key
        self.pulpoo_api_key = pulpoo_api_key

    async def schedule_appointment(
        self,
        user_name: str,
        user_email: str,
        appointment_topic: str,
        preferred_date: str,
        summary_notes: Optional[str] = None,
    ) -> dict:
        """
        Schedule an appointment in Pulpoo.

        Args:
            user_name: Customer name
            user_email: Customer email
            appointment_topic: What the appointment is about
            preferred_date: ISO format datetime (e.g., "2025-11-15T14:30:00")
            summary_notes: Brief summary of conversation/discussion

        Returns:
            Dictionary with success status and appointment details
        """
        try:
            logger.info(f"Scheduling appointment for {user_email}")

            if not self.pulpoo_api_key:
                logger.error("Pulpoo API key not configured")
                return {"success": False, "error": "API key missing"}

            # Parse the date
            try:
                scheduled_time = datetime.fromisoformat(preferred_date)
            except (ValueError, TypeError):
                logger.error(f"Invalid date format: {preferred_date}")
                return {"success": False, "error": "Invalid date format"}

            # Set deadline to 24 hours after appointment
            deadline = (scheduled_time + timedelta(hours=24)).isoformat() + "Z"

            # Build description with user info and summary
            description = f"""Customer: {user_name}
Email: {user_email}
Topic: {appointment_topic}
Scheduled: {scheduled_time.strftime('%B %d, %Y at %I:%M %p')}"""

            if summary_notes:
                description += f"""

Notes:
{summary_notes}"""

            # Create task in Pulpoo
            async with aiohttp.ClientSession() as session:
                headers = {
                    "X-API-Key": self.pulpoo_api_key,
                    "Content-Type": "application/json",
                }

                payload = {
                    "title": f"Appointment: {appointment_topic}",
                    "description": description,
                    "assigned_to_email": "perezmd324@gmail.com",
                    "deadline": deadline,
                    "importance": "HIGH",
                }

                async with session.post(
                    get_voice_config().pulpoo_api_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        appointment_id = result.get("id", f"apt_{scheduled_time.timestamp()}")
                        
                        logger.info(f"✓ Appointment created: {appointment_id}")

                        return {
                            "success": True,
                            "appointment_id": appointment_id,
                            "scheduled_time": scheduled_time.isoformat(),
                            "message": f"Perfect! Your appointment is scheduled for {scheduled_time.strftime('%B %d at %I:%M %p')}",
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Pulpoo API error: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"Failed to schedule (error {response.status})",
                        }

        except Exception as e:
            logger.error(f"Error scheduling appointment: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
