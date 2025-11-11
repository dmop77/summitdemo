"""
Web scraping utility using OpenAI for intelligent content extraction.

This module handles:
- Fetching web content
- Extracting and summarizing content using OpenAI
- Generating embeddings for semantic search
"""

import logging
from typing import Optional, Tuple
from datetime import datetime

import httpx
from openai import AsyncOpenAI
from bs4 import BeautifulSoup

from schemas import ScrapedContent

logger = logging.getLogger(__name__)


class WebScraper:
    """Web scraper with OpenAI-powered content extraction."""

    def __init__(self, openai_api_key: str, max_pages: int = 5):
        """
        Initialize the web scraper.

        Args:
            openai_api_key: OpenAI API key for content processing
            max_pages: Maximum number of pages to crawl per domain
        """
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.max_pages = max_pages
        self.visited_urls = set()

    async def scrape_url(self, url: str) -> Optional[ScrapedContent]:
        """
        Scrape a website and extract meaningful content.

        Args:
            url: Website URL to scrape

        Returns:
            ScrapedContent object with extracted information
        """
        try:
            logger.info(f"Starting web scrape for: {url}")

            # Fetch the main page
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0),
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style tags
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract text content
            text_content = soup.get_text(separator="\n", strip=True)
            title = soup.find("title")
            title_text = title.string if title else "Unknown"

            # Extract main heading if no title
            if not title:
                h1 = soup.find("h1")
                title_text = h1.get_text(strip=True) if h1 else "Unknown"

            # Limit content size for API
            content_preview = text_content[:4000]

            logger.info(f"Extracted {len(text_content)} characters from {url}")

            # Generate summary using OpenAI
            summary = await self._generate_summary(title_text, content_preview)

            return ScrapedContent(
                url=url,
                title=title_text,
                content=content_preview,
                summary=summary,
                pages_crawled=1,
                urls=[url],
            )

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None

    async def _generate_summary(self, title: str, content: str) -> str:
        """
        Generate AI summary of scraped content.

        Args:
            title: Page title
            content: Page content

        Returns:
            AI-generated summary
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at summarizing web content. "
                        "Provide a concise, clear summary of the main points in 2-3 sentences.",
                    },
                    {
                        "role": "user",
                        "content": f"Title: {title}\n\nContent:\n{content}",
                    },
                ],
                max_tokens=300,
                temperature=0.7,
            )

            summary = response.choices[0].message.content
            logger.info(f"Generated summary: {summary[:100]}...")
            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Unable to generate summary"

    async def generate_embedding(self, text: str) -> list:
        """
        Generate embedding for text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )

            embedding = response.data[0].embedding
            logger.info(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    async def scrape_and_embed(self, url: str) -> Optional[Tuple[ScrapedContent, list]]:
        """
        Scrape a URL and generate embeddings for its content.

        Args:
            url: Website URL to scrape

        Returns:
            Tuple of (ScrapedContent, embedding vector)
        """
        scraped = await self.scrape_url(url)
        if not scraped:
            return None

        # Generate embedding from summary for better semantic representation
        embedding_text = f"{scraped.title}. {scraped.summary}"
        embedding = await self.generate_embedding(embedding_text)

        if not embedding:
            logger.warning("Failed to generate embedding, returning without it")
            return (scraped, [])

        return (scraped, embedding)
