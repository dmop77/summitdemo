"""User information schema."""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional


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
    website_summary: Optional[str] = Field(None, description="Summary of scraped website content")
