"""
Simplified agent tools for appointment scheduling.

Tools:
- schedule_appointment: Create appointment in Pulpoo with user details and summary
"""

import logging
from typing import Optional
from datetime import datetime, timedelta, timezone

import aiohttp
from config import get_voice_config

logger = logging.getLogger(__name__)


def parse_appointment_time(time_str: str) -> Optional[str]:
    """
    Parse natural language or ISO format time strings and convert to ISO format.

    Args:
        time_str: Time string (e.g., "2025-11-15T14:30:00", "tomorrow at 2pm", "next Monday at 3pm")

    Returns:
        ISO format datetime string or None if parsing fails
    """
    if not time_str:
        logger.warning("parse_appointment_time: time_str is empty")
        return None

    # Ensure it's a string
    time_str = str(time_str).strip()
    if not time_str:
        return None

    try:
        # Try parsing as ISO format first
        if 'T' in time_str or time_str.endswith('Z'):
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            logger.info(f"Parsed ISO format: {time_str} → {dt.isoformat()}")
            return dt.isoformat()
    except (ValueError, AttributeError) as e:
        logger.debug(f"ISO format parsing failed: {e}")
        pass

    # If not ISO, try to parse natural language
    time_str_lower = time_str.lower().strip()
    now = datetime.now()

    try:
        # Handle relative times
        if "tomorrow" in time_str_lower:
            # Remove time part and parse just the time
            parts = time_str_lower.split("tomorrow")
            time_part = parts[-1].strip() if len(parts) > 1 else "9:00 am"

            tomorrow = now + timedelta(days=1)

            # Parse time (e.g., "at 2:30 pm" → "14:30" or "2 pm" → "14:00")
            if "am" in time_part or "pm" in time_part:
                time_part = time_part.replace("at", "").replace(".", "").strip()

                # Try multiple time formats
                time_formats = ["%I:%M %p", "%I %p", "%I:%M%p", "%I%p"]
                time_obj = None
                for fmt in time_formats:
                    try:
                        time_obj = datetime.strptime(time_part, fmt).time()
                        break
                    except ValueError:
                        continue

                if time_obj:
                    appointment_dt = datetime.combine(tomorrow.date(), time_obj)
                    return appointment_dt.isoformat()

        elif "next week" in time_str_lower or "next monday" in time_str_lower:
            # Default to Monday 10am next week
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            next_week_date = now + timedelta(days=days_until_monday)

            # Try to extract time
            time_part = "10:00 am"
            for pattern in ["at ", "@ ", "at"]:
                if pattern in time_str_lower:
                    time_part = time_str_lower.split(pattern)[-1].replace(".", "").strip()
                    break

            # Try multiple time formats for flexibility
            time_formats = ["%I:%M %p", "%I %p", "%I:%M%p", "%I%p"]
            time_obj = None
            for fmt in time_formats:
                try:
                    time_obj = datetime.strptime(time_part, fmt).time()
                    break
                except ValueError:
                    continue

            if time_obj:
                appointment_dt = datetime.combine(next_week_date.date(), time_obj)
                return appointment_dt.isoformat()
            else:
                # Default to 10:00 am if parsing fails
                default_time = datetime.strptime("10:00 am", "%I:%M %p").time()
                appointment_dt = datetime.combine(next_week_date.date(), default_time)
                return appointment_dt.isoformat()

        else:
            # Try parsing as full datetime string
            dt = datetime.strptime(time_str_lower, "%Y-%m-%d %I:%M %p")
            return dt.isoformat()

    except Exception as e:
        logger.warning(f"Failed to parse time: {time_str} - {e}")
        return None


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

            # Parse the date and validate it's in the future
            try:
                scheduled_time = datetime.fromisoformat(preferred_date)

                # Get current time (use UTC for consistency)
                # Handle both naive and timezone-aware datetimes
                if scheduled_time.tzinfo is None:
                    # Naive datetime - use local timezone
                    now = datetime.now()
                else:
                    # Timezone-aware datetime - use UTC
                    now = datetime.now(timezone.utc)

                # Add a 5-minute buffer to account for processing time
                now_with_buffer = now + timedelta(minutes=5)

                # Validate that appointment is in the future
                if scheduled_time <= now_with_buffer:
                    logger.warning(f"Appointment time too close or in past: {preferred_date} (now: {now})")
                    # Don't reject - allow it but warn the user
                    logger.info(f"⚠️ Scheduling appointment for: {scheduled_time}")

            except (ValueError, TypeError) as e:
                logger.error(f"Invalid date format: {preferred_date} - {e}")
                return {"success": False, "error": "Invalid date format. Please provide time in format like '2025-11-13 2:30 PM'"}

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
                    "assigned_to_email": "efernandez@pulpoo.com",
                    "customer_email": user_email,
                    "canal": "Engineering",
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
