"""Web scraper API request/response schemas."""

from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import Optional

from .content import ScrapedContent


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
