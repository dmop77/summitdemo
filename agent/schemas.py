"""
Data schemas for web scraping, user information, and voice agent interactions.

This module defines Pydantic models for:
- Web scraping results and embeddings
- User information collection
- Scheduling and appointment management
- Voice agent interaction data
"""

from pydantic import BaseModel, EmailStr, Field, HttpUrl, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ScrapedContent(BaseModel):
    """Schema for scraped website content."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com",
                "title": "Example Website",
                "content": "The main content text...",
                "summary": "A brief summary",
                "pages_crawled": 2,
                "urls": ["https://example.com", "https://example.com/about"],
            }
        }
    )

    url: HttpUrl
    title: str = Field(..., description="Page title or main heading")
    content: str = Field(..., description="Extracted text content from the page")
    summary: Optional[str] = Field(None, description="AI-generated summary of the content")
    pages_crawled: int = Field(default=1, description="Number of pages crawled")
    urls: List[str] = Field(default_factory=list, description="List of URLs crawled")


class UserInfo(BaseModel):
    """Schema for collecting user information during voice interaction."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "website_url": "https://example.com",
                "phone_number": "+1-555-0123",
                "issue_summary": "Need to discuss website optimization",
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    website_url: Optional[str] = Field(None, description="Website URL provided by user")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    issue_summary: Optional[str] = Field(None, description="Summary of user's issue or request")


class ScrapedLinkRecord(BaseModel):
    """Schema for storing scraped link data in Supabase."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_name": "John Doe",
                "user_email": "john@example.com",
                "url": "https://example.com",
                "summary": "Example company provides...",
                "embedding": [0.123, -0.456, 0.789],
                "created_at": "2025-11-11T12:00:00Z",
            }
        }
    )

    id: Optional[UUID] = Field(None, description="Record UUID (auto-generated)")
    user_name: str = Field(..., description="User's name")
    user_email: EmailStr = Field(..., description="User's email")
    url: HttpUrl = Field(..., description="Website URL that was scraped")
    summary: str = Field(..., description="Content summary from web scraper")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding of content")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Timestamp")


class AppointmentSlot(BaseModel):
    """Schema for available appointment slots."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "slot_id": "slot_001",
                "date_time": "2025-11-15T14:00:00Z",
                "duration_minutes": 30,
                "status": "available",
            }
        }
    )

    slot_id: str = Field(..., description="Unique identifier for the slot")
    date_time: datetime = Field(..., description="Date and time of the appointment")
    duration_minutes: int = Field(default=30, description="Duration of appointment in minutes")
    status: str = Field(default="available", description="Status: available, booked, unavailable")


class ScheduledAppointment(BaseModel):
    """Schema for scheduled appointments via Pulpo."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "appointment_id": "apt_12345",
                "user_name": "John Doe",
                "user_email": "john@example.com",
                "scheduled_time": "2025-11-15T14:00:00Z",
                "duration_minutes": 30,
                "topic": "Website Discussion",
                "topic_summary": "Discussed optimization strategies",
                "notes": "Customer interested in Q1 implementation",
            }
        }
    )

    appointment_id: str = Field(..., description="Unique appointment ID from Pulpo")
    user_name: str = Field(..., description="User's name")
    user_email: EmailStr = Field(..., description="User's email")
    scheduled_time: datetime = Field(..., description="Scheduled appointment time")
    duration_minutes: int = Field(default=30, description="Duration in minutes")
    topic: str = Field(..., description="Topic or subject of the appointment")
    topic_summary: Optional[str] = Field(None, description="Summary of scraped content discussed")
    notes: Optional[str] = Field(None, description="Additional notes")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class RescheduleRequest(BaseModel):
    """Schema for appointment rescheduling requests."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "appointment_id": "apt_12345",
                "original_time": "2025-11-15T14:00:00Z",
                "proposed_time": "2025-11-16T10:00:00Z",
                "reason": "Client conflict",
            }
        }
    )

    appointment_id: str = Field(..., description="ID of appointment to reschedule")
    original_time: datetime = Field(..., description="Current appointment time")
    proposed_time: Optional[datetime] = Field(None, description="Proposed new time")
    reason: Optional[str] = Field(None, description="Reason for rescheduling")


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
            }
        }
    )

    session_id: str = Field(..., description="Unique session ID")
    user_info: Optional[UserInfo] = Field(None, description="Collected user information")
    scraped_content: Optional[ScrapedContent] = Field(None, description="Scraped website content")
    conversation_history: List[VoiceAgentMessage] = Field(default_factory=list)
    scheduled_appointment: Optional[ScheduledAppointment] = Field(None)
    current_state: str = Field(default="greeting", description="Current conversation state")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WebScraperRequest(BaseModel):
    """Schema for web scraper API requests."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com",
                "max_pages": 5,
                "include_summary": True,
            }
        }
    )

    url: HttpUrl = Field(..., description="Website URL to scrape")
    max_pages: int = Field(default=5, description="Maximum pages to crawl")
    include_summary: bool = Field(default=True, description="Generate AI summary")


class WebScraperResponse(BaseModel):
    """Schema for web scraper API responses."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {
                    "url": "https://example.com",
                    "title": "Example",
                    "content": "...",
                    "pages_crawled": 2,
                },
                "error": None,
                "processing_time_seconds": 3.45,
            }
        }
    )

    success: bool = Field(..., description="Whether scraping was successful")
    data: Optional[ScrapedContent] = Field(None, description="Scraped content data")
    error: Optional[str] = Field(None, description="Error message if failed")
    processing_time_seconds: float = Field(..., description="Time taken to scrape")
