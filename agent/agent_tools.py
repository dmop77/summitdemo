"""
Tool functions for Pydantic AI agent.

Provides:
- Web scraping tool
- Appointment scheduling tool
- User information collection tool
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

import aiohttp
from pydantic_ai import RunContext

from schemas import UserInfo, ScheduledAppointment, ScrapedContent
from web_scraper import WebScraper
from config import get_voice_config

logger = logging.getLogger(__name__)


class AgentTools:
    """Collection of tools for the voice agent."""

    def __init__(self, openai_api_key: str, deepgram_api_key: str, pulpoo_api_key: str):
        """
        Initialize agent tools.

        Args:
            openai_api_key: OpenAI API key
            deepgram_api_key: Deepgram API key (for context)
            pulpoo_api_key: Pulpoo API key for appointment creation
        """
        self.openai_api_key = openai_api_key
        self.deepgram_api_key = deepgram_api_key
        self.pulpoo_api_key = pulpoo_api_key
        self.web_scraper = WebScraper(openai_api_key)

    async def scrape_website(self, url: str) -> dict:
        """
        Scrape a website and return structured content.

        Args:
            url: Website URL to scrape

        Returns:
            Dictionary with scraped content
        """
        try:
            logger.info(f"Tool: Scraping website {url}")

            result = await self.web_scraper.scrape_and_embed(url)
            if not result:
                return {"success": False, "error": "Failed to scrape website"}

            scraped_content, embedding = result

            return {
                "success": True,
                "url": str(scraped_content.url),
                "title": scraped_content.title,
                "summary": scraped_content.summary,
                "content_preview": scraped_content.content[:500],
                "pages_crawled": scraped_content.pages_crawled,
            }

        except Exception as e:
            logger.error(f"Error in scrape_website tool: {e}")
            return {"success": False, "error": str(e)}

    async def create_appointment(
        self,
        topic: str,
        preferred_date: Optional[str] = None,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
    ) -> dict:
        """
        Create an appointment in Pulpoo.

        Args:
            topic: Appointment topic/subject (required)
            preferred_date: Preferred date/time as ISO format string (e.g., "2025-11-15T14:30:00") or natural language (e.g., "next Monday at 2 PM")
            user_name: Customer's name (will be provided by agent context - do not ask user)
            user_email: Customer's email (will be provided by agent context - do not ask user)

        Returns:
            Dictionary with appointment details
        """
        try:
            # Use provided values or get from agent context
            # In real usage, the agent will have these from ConversationContext
            if not user_name:
                user_name = "User"  # Fallback
            if not user_email:
                user_email = "user@example.com"  # Fallback

            logger.info(f"Tool: Creating appointment for {user_email} - Topic: {topic}")

            if not self.pulpoo_api_key:
                logger.warning("Pulpoo API key not configured")
                return {
                    "success": False,
                    "error": "Appointment service not configured",
                }

            # Calculate appointment time
            if preferred_date:
                try:
                    # Try ISO format first
                    scheduled_time = datetime.fromisoformat(preferred_date)
                except ValueError:
                    try:
                        # Try parsing as a date string with basic patterns
                        # This is a simple fallback - LLM should provide ISO format when possible
                        logger.warning(f"Could not parse preferred_date '{preferred_date}' as ISO format. Using default.")
                        scheduled_time = datetime.utcnow() + timedelta(days=1)
                        scheduled_time = scheduled_time.replace(hour=10, minute=0, second=0)
                    except Exception as e:
                        logger.error(f"Error parsing date: {e}")
                        scheduled_time = datetime.utcnow() + timedelta(days=1)
                        scheduled_time = scheduled_time.replace(hour=10, minute=0, second=0)
            else:
                # Default: tomorrow at 10 AM if no date provided
                logger.warning("No preferred_date provided. Using default (tomorrow at 10 AM).")
                scheduled_time = datetime.utcnow() + timedelta(days=1)
                scheduled_time = scheduled_time.replace(hour=10, minute=0, second=0)

            deadline = (scheduled_time + timedelta(hours=24)).isoformat() + "Z"

            # Create task in Pulpoo
            async with aiohttp.ClientSession() as session:
                headers = {
                    "X-API-Key": self.pulpoo_api_key,
                    "Content-Type": "application/json",
                }

                payload = {
                    "title": f"Appointment: {topic}",
                    "description": f"Customer: {user_name}\nEmail: {user_email}\n"
                    f"Topic: {topic}\n"
                    f"Scheduled: {scheduled_time.isoformat()}",
                    "assigned_to_email": "support@pulpoo.com",
                    "importance": "HIGH",
                    "canal": "Voice Assistant",
                    "deadline": deadline,
                    "customer_email": user_email,
                    "customer_name": user_name,
                }

                async with session.post(
                    get_voice_config().pulpoo_api_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        logger.info(f"Appointment created: {result}")

                        return {
                            "success": True,
                            "appointment_id": result.get("id", "apt_" + str(scheduled_time.timestamp())),
                            "scheduled_time": scheduled_time.isoformat(),
                            "duration_minutes": duration_minutes,
                            "message": f"Appointment scheduled for {scheduled_time.strftime('%B %d at %I:%M %p')}",
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Pulpoo error: {response.status} - {error_text}")

                        return {
                            "success": False,
                            "error": f"Failed to create appointment: {response.status}",
                        }

        except Exception as e:
            logger.error(f"Error in create_appointment tool: {e}")
            return {"success": False, "error": str(e)}

    async def get_available_slots(self) -> dict:
        """
        Get available appointment slots.

        This is a mock implementation - integrate with your actual scheduling system.

        Returns:
            Dictionary with available slots
        """
        try:
            logger.info("Tool: Getting available appointment slots")

            # Mock available slots (next 7 days)
            slots = []
            start_date = datetime.utcnow().replace(hour=9, minute=0, second=0)

            for day in range(7):
                for hour in [9, 11, 14, 16]:
                    slot_time = start_date + timedelta(days=day, hours=hour)
                    slots.append(
                        {
                            "slot_id": f"slot_{len(slots)}",
                            "date_time": slot_time.isoformat(),
                            "time_display": slot_time.strftime("%A, %B %d at %I:%M %p"),
                        }
                    )

            return {
                "success": True,
                "available_slots": slots[:10],  # Return first 10 slots
                "message": f"Found {len(slots)} available slots",
            }

        except Exception as e:
            logger.error(f"Error in get_available_slots tool: {e}")
            return {"success": False, "error": str(e)}
