"""Supabase database schemas."""

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


class UserRecord(BaseModel):
    """Database schema for users table."""

    model_config = ConfigDict(json_schema_extra={"table": "users"})

    id: Optional[UUID] = Field(None, description="Primary key")
    name: str = Field(..., description="User's full name")
    email: EmailStr = Field(..., description="User's email (unique)")
    website_url: Optional[str] = Field(None, description="User's website URL")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class SessionRecord(BaseModel):
    """Database schema for sessions table."""

    model_config = ConfigDict(json_schema_extra={"table": "sessions"})

    id: Optional[UUID] = Field(None, description="Primary key")
    user_id: UUID = Field(..., description="Foreign key to users")
    session_id: str = Field(..., description="Unique session identifier")
    website_summary: Optional[str] = Field(None, description="Website content summary")
    status: str = Field(default="active", description="Session status")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class ScrapedContentRecord(BaseModel):
    """Database schema for scraped_content table."""

    model_config = ConfigDict(json_schema_extra={"table": "scraped_content"})

    id: Optional[UUID] = Field(None, description="Primary key")
    user_id: UUID = Field(..., description="Foreign key to users")
    session_id: UUID = Field(..., description="Foreign key to sessions")
    url: str = Field(..., description="URL that was scraped")
    title: Optional[str] = Field(None, description="Page title")
    summary: Optional[str] = Field(None, description="Content summary")
    content: Optional[str] = Field(None, description="Full page content")
    content_hash: Optional[str] = Field(None, description="Hash for duplicate detection")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class ConversationMessageRecord(BaseModel):
    """Database schema for conversation_messages table."""

    model_config = ConfigDict(json_schema_extra={"table": "conversation_messages"})

    id: Optional[UUID] = Field(None, description="Primary key")
    session_id: UUID = Field(..., description="Foreign key to sessions")
    user_id: UUID = Field(..., description="Foreign key to users")
    sender: str = Field(..., description="'user' or 'agent'")
    message_text: str = Field(..., description="Message content")
    transcript: Optional[str] = Field(None, description="Original transcript (for user messages)")
    audio_duration_ms: Optional[int] = Field(None, description="Audio duration in milliseconds")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class AppointmentRecord(BaseModel):
    """Database schema for appointments table."""

    model_config = ConfigDict(json_schema_extra={"table": "appointments"})

    id: Optional[UUID] = Field(None, description="Primary key")
    user_id: UUID = Field(..., description="Foreign key to users")
    session_id: UUID = Field(..., description="Foreign key to sessions")
    topic: str = Field(..., description="Appointment topic")
    preferred_date: datetime = Field(..., description="Scheduled appointment time")
    status: str = Field(default="scheduled", description="Appointment status")
    summary_notes: Optional[str] = Field(None, description="Conversation summary")
    external_id: Optional[str] = Field(None, description="External system ID (e.g., Pulpoo)")
    pulpoo_response: Optional[dict] = Field(None, description="Response from Pulpoo API")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class AnalyticsRecord(BaseModel):
    """Schema for user analytics."""

    model_config = ConfigDict(json_schema_extra={"description": "User statistics"})

    sessions_count: int = Field(default=0, description="Number of sessions")
    messages_count: int = Field(default=0, description="Total messages sent")
    appointments_count: int = Field(default=0, description="Appointments scheduled")
    last_session: Optional[datetime] = Field(None, description="Last session date")
