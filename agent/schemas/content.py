"""Web scraping content schemas."""

from pydantic import BaseModel, Field, HttpUrl, EmailStr, ConfigDict
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
