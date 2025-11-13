"""Appointment and scheduling schemas."""

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime


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
