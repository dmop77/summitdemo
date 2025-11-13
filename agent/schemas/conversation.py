"""Conversation and context schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

from .user import UserInfo
from .content import ScrapedContent
from .appointment import ScheduledAppointment


class VoiceAgentMessage(BaseModel):
    """Schema for voice agent messages and interactions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": "msg_001",
                "session_id": "session_xyz123",
                "speaker": "agent",
                "text": "Hi! I just read the page you shared about example.com",
                "timestamp": "2025-11-11T12:00:00Z",
            }
        }
    )

    message_id: str = Field(..., description="Unique message ID")
    session_id: str = Field(..., description="Voice session ID")
    speaker: str = Field(..., description="'user' or 'agent'")
    text: str = Field(..., description="Message text content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationContext(BaseModel):
    """Schema for tracking conversation context in voice sessions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session_xyz123",
                "user_info": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "website_url": "https://example.com",
                },
                "scraped_content": {
                    "url": "https://example.com",
                    "title": "Example",
                    "content": "...",
                },
                "conversation_history": [],
                "current_state": "greeting",
                "appointment_booking_state": "idle",
                "pending_appointment_topic": None,
                "selected_appointment_slot": None,
            }
        }
    )

    session_id: str = Field(..., description="Unique session ID")
    user_info: Optional[UserInfo] = Field(None, description="Collected user information")
    scraped_content: Optional[ScrapedContent] = Field(None, description="Scraped website content")
    conversation_history: List[VoiceAgentMessage] = Field(default_factory=list)
    scheduled_appointment: Optional[ScheduledAppointment] = Field(None)
    current_state: str = Field(default="greeting", description="Current conversation state")

    # Appointment booking state tracking
    appointment_booking_state: str = Field(
        default="idle",
        description="State of appointment booking: idle, topic_provided, slots_shown, slot_selected, confirmed, completed"
    )
    pending_appointment_topic: Optional[str] = Field(
        None,
        description="Topic provided by user before showing slots"
    )
    selected_appointment_slot: Optional[dict] = Field(
        None,
        description="Selected appointment slot from available options (contains date_time and time_display)"
    )
    appointment_confirmation_awaited: bool = Field(
        default=False,
        description="Whether we're waiting for user confirmation of appointment details"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
