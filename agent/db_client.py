"""
Supabase database client for caching user and session data.
Handles all database operations for production deployment.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from supabase import create_client, Client
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Manages all database operations for voice agent."""

    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize Supabase client.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key (anon or service role)
        """
        self.client: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")

    # ========== USER OPERATIONS ==========

    async def get_or_create_user(
        self,
        email: str,
        name: str,
        website_url: str
    ) -> Dict[str, Any]:
        """
        Get existing user or create new one.

        Args:
            email: User email
            name: User name
            website_url: User's website

        Returns:
            User record with id
        """
        try:
            # Try to get existing user
            response = self.client.table("users").select("*").eq("email", email).execute()

            if response.data:
                logger.info(f"Found existing user: {email}")
                return response.data[0]

            # Create new user
            new_user = {
                "name": name,
                "email": email,
                "website_url": website_url,
            }
            response = self.client.table("users").insert(new_user).execute()
            logger.info(f"Created new user: {email}")
            return response.data[0]

        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            raise

    # ========== SESSION OPERATIONS ==========

    async def create_session(
        self,
        user_id: str,
        session_id: str,
        website_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new session.

        Args:
            user_id: User UUID
            session_id: Unique session identifier
            website_summary: Optional website summary

        Returns:
            Session record
        """
        try:
            session_data = {
                "user_id": user_id,
                "session_id": session_id,
                "website_summary": website_summary,
                "status": "active",
            }
            response = self.client.table("sessions").insert(session_data).execute()
            logger.info(f"Created session: {session_id}")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by session_id."""
        try:
            response = self.client.table("sessions").select("*").eq("session_id", session_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None

    async def update_session_status(
        self,
        session_id: str,
        status: str
    ) -> None:
        """Update session status (active, completed, abandoned)."""
        try:
            self.client.table("sessions").update(
                {"status": status}
            ).eq("session_id", session_id).execute()
            logger.info(f"Updated session {session_id} status to {status}")
        except Exception as e:
            logger.error(f"Error updating session status: {e}")

    # ========== SCRAPED CONTENT OPERATIONS ==========

    async def save_scraped_content(
        self,
        user_id: str,
        session_id: str,
        url: str,
        title: str,
        summary: str,
        content: str,
        content_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save scraped website content.

        Args:
            user_id: User UUID
            session_id: Session UUID
            url: Website URL
            title: Page title
            summary: Content summary
            content: Full content
            content_hash: Optional hash to detect duplicates

        Returns:
            Scraped content record
        """
        try:
            scraped_data = {
                "user_id": user_id,
                "session_id": session_id,
                "url": url,
                "title": title,
                "summary": summary,
                "content": content,
                "content_hash": content_hash,
            }
            response = self.client.table("scraped_content").insert(scraped_data).execute()
            logger.info(f"Saved scraped content for {url}")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error saving scraped content: {e}")
            raise

    async def get_scraped_content(
        self,
        user_id: str,
        limit: int = 5
    ) -> list[Dict[str, Any]]:
        """Get recent scraped content for user."""
        try:
            response = (
                self.client.table("scraped_content")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Error getting scraped content: {e}")
            return []

    # ========== CONVERSATION OPERATIONS ==========

    async def save_message(
        self,
        session_id: str,
        user_id: str,
        sender: str,  # "user" or "agent"
        message_text: str,
        transcript: Optional[str] = None,
        audio_duration_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Save conversation message.

        Args:
            session_id: Session UUID
            user_id: User UUID
            sender: "user" or "agent"
            message_text: Message content
            transcript: Original transcript (for user messages)
            audio_duration_ms: Audio length in milliseconds

        Returns:
            Message record
        """
        try:
            message_data = {
                "session_id": session_id,
                "user_id": user_id,
                "sender": sender,
                "message_text": message_text,
                "transcript": transcript,
                "audio_duration_ms": audio_duration_ms,
            }
            response = self.client.table("conversation_messages").insert(message_data).execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            raise

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> list[Dict[str, Any]]:
        """Get conversation history for session."""
        try:
            response = (
                self.client.table("conversation_messages")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    # ========== APPOINTMENT OPERATIONS ==========

    async def create_appointment(
        self,
        user_id: str,
        session_id: str,
        topic: str,
        preferred_date: str,
        summary_notes: Optional[str] = None,
        pulpoo_response: Optional[Dict[str, Any]] = None,
        external_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create appointment record.

        Args:
            user_id: User UUID
            session_id: Session UUID
            topic: Appointment topic
            preferred_date: ISO format datetime
            summary_notes: Conversation summary
            pulpoo_response: Response from Pulpoo API
            external_id: ID from external system (Pulpoo)

        Returns:
            Appointment record
        """
        try:
            appointment_data = {
                "user_id": user_id,
                "session_id": session_id,
                "topic": topic,
                "preferred_date": preferred_date,
                "status": "scheduled",
                "summary_notes": summary_notes,
                "pulpoo_response": pulpoo_response,
                "external_id": external_id,
            }
            response = self.client.table("appointments").insert(appointment_data).execute()
            logger.info(f"Created appointment for user {user_id}: {topic}")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise

    async def get_appointments(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 10
    ) -> list[Dict[str, Any]]:
        """
        Get user appointments.

        Args:
            user_id: User UUID
            status: Filter by status (scheduled, completed, cancelled)
            limit: Max results

        Returns:
            List of appointments
        """
        try:
            query = self.client.table("appointments").select("*").eq("user_id", user_id)

            if status:
                query = query.eq("status", status)

            response = (
                query
                .order("preferred_date", desc=False)
                .limit(limit)
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Error getting appointments: {e}")
            return []

    async def update_appointment(
        self,
        appointment_id: str,
        **updates
    ) -> Dict[str, Any]:
        """Update appointment record."""
        try:
            response = self.client.table("appointments").update(updates).eq("id", appointment_id).execute()
            logger.info(f"Updated appointment {appointment_id}")
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error updating appointment: {e}")
            raise

    # ========== ANALYTICS & REPORTING ==========

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            # Get sessions count
            sessions = self.client.table("sessions").select("count").eq("user_id", user_id).execute()
            sessions_count = sessions.count if hasattr(sessions, 'count') else 0

            # Get messages count
            messages = self.client.table("conversation_messages").select("count").eq("user_id", user_id).execute()
            messages_count = messages.count if hasattr(messages, 'count') else 0

            # Get appointments count
            appointments = self.client.table("appointments").select("count").eq("user_id", user_id).execute()
            appointments_count = appointments.count if hasattr(appointments, 'count') else 0

            return {
                "sessions_count": sessions_count,
                "messages_count": messages_count,
                "appointments_count": appointments_count,
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}

    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            response = self.client.table("users").select("count").limit(1).execute()
            logger.info("Database health check: OK")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
