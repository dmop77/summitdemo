"""Data schemas for voice agent and web scraping."""

from .user import UserInfo
from .content import ScrapedContent, ScrapedLinkRecord
from .appointment import AppointmentSlot, ScheduledAppointment, RescheduleRequest
from .conversation import ConversationContext, VoiceAgentMessage
from .web_scraper import WebScraperRequest, WebScraperResponse
from .supabase import (
    UserRecord,
    SessionRecord,
    ScrapedContentRecord,
    ConversationMessageRecord,
    AppointmentRecord,
    AnalyticsRecord,
)

__all__ = [
    # User/Content schemas
    "UserInfo",
    "ScrapedContent",
    "ScrapedLinkRecord",
    # Appointment schemas
    "AppointmentSlot",
    "ScheduledAppointment",
    "RescheduleRequest",
    # Conversation schemas
    "ConversationContext",
    "VoiceAgentMessage",
    # Web scraper schemas
    "WebScraperRequest",
    "WebScraperResponse",
    # Supabase database schemas
    "UserRecord",
    "SessionRecord",
    "ScrapedContentRecord",
    "ConversationMessageRecord",
    "AppointmentRecord",
    "AnalyticsRecord",
]
