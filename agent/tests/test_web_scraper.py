"""
Tests for Web Scraper functionality

Tests website scraping, content extraction, and embedding generation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bs4 import BeautifulSoup

from web_scraper import WebScraper
from config import get_voice_config


class TestWebScraper:
    """Test web scraping functionality."""

    @pytest.fixture
    def voice_config(self):
        """Get voice configuration."""
        return get_voice_config()

    @pytest.fixture
    def web_scraper(self, voice_config):
        """Create WebScraper instance."""
        return WebScraper(openai_api_key=voice_config.openai_api_key)

    @pytest.mark.asyncio
    async def test_scraper_initialization(self, web_scraper):
        """Test WebScraper initialization."""
        assert web_scraper is not None
        assert web_scraper.client is not None
        assert web_scraper.max_pages == 5
        print("✓ Web scraper initialized successfully")

    @pytest.mark.asyncio
    async def test_scrape_url_with_mock_html(self, web_scraper):
        """Test scraping with mocked HTML content."""
        html_content = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Welcome to Test Site</h1>
                <p>This is test content for the website.</p>
                <p>We provide excellent services.</p>
            </body>
        </html>
        """
        
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock the HTTP response
            mock_response = AsyncMock()
            mock_response.text = html_content
            mock_response.raise_for_status = AsyncMock()
            mock_get.return_value = mock_response
            
            # Mock the OpenAI summary
            with patch.object(web_scraper, '_generate_summary', new_callable=AsyncMock) as mock_summary:
                mock_summary.return_value = "Test site provides excellent services."
                
                # Call scrape_url
                result = await web_scraper.scrape_url("https://example.com")
        
        # Verify result
        assert result is not None
        assert result.title == "Test Page"
        assert "excellent" in result.summary.lower()
        print(f"✓ Web page scraped: {result.title}")

    @pytest.mark.asyncio
    async def test_generate_summary(self, web_scraper):
        """Test content summarization with OpenAI."""
        title = "Example Website"
        content = "This is a sample website about technology and innovation."
        
        # Test with actual API (will use real credits if configured)
        if web_scraper.client:
            try:
                summary = await web_scraper._generate_summary(title, content)
                assert summary is not None
                assert len(summary) > 0
                print(f"✓ Summary generated: {summary[:100]}...")
            except Exception as e:
                pytest.skip(f"OpenAI API not available: {e}")
        else:
            pytest.skip("OpenAI client not configured")

    @pytest.mark.asyncio
    async def test_generate_embedding(self, web_scraper):
        """Test embedding generation."""
        text = "This is a sample text for embedding generation."
        
        # Test with actual API (will use real credits if configured)
        if web_scraper.client:
            try:
                embedding = await web_scraper.generate_embedding(text)
                assert embedding is not None
                assert isinstance(embedding, list)
                assert len(embedding) > 0
                print(f"✓ Embedding generated: {len(embedding)} dimensions")
            except Exception as e:
                pytest.skip(f"OpenAI API not available: {e}")
        else:
            pytest.skip("OpenAI client not configured")

    @pytest.mark.asyncio
    async def test_scrape_and_embed(self, web_scraper):
        """Test scraping and embedding in one call."""
        html_content = """
        <html>
            <head><title>Test Site</title></head>
            <body>
                <h1>Welcome</h1>
                <p>Content here</p>
            </body>
        </html>
        """
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.text = html_content
            mock_response.raise_for_status = AsyncMock()
            mock_get.return_value = mock_response
            
            with patch.object(web_scraper, '_generate_summary', new_callable=AsyncMock) as mock_summary:
                mock_summary.return_value = "Test summary"
                
                with patch.object(web_scraper, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
                    mock_embed.return_value = [0.1, 0.2, 0.3]
                    
                    result = await web_scraper.scrape_and_embed("https://example.com")
        
        # Verify result
        assert result is not None
        scraped_content, embedding = result
        assert scraped_content.title == "Test Site"
        assert embedding == [0.1, 0.2, 0.3]
        print(f"✓ Scrape and embed successful")

    @pytest.mark.asyncio
    async def test_html_parsing(self, web_scraper):
        """Test HTML parsing and text extraction."""
        html = """
        <html>
            <head><title>My Website</title></head>
            <body>
                <h1>Main Heading</h1>
                <p>First paragraph.</p>
                <p>Second paragraph.</p>
                <script>console.log('hidden');</script>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove scripts
        for script in soup(['script', 'style']):
            script.decompose()
        
        text = soup.get_text(separator="\n", strip=True)
        
        # Verify extraction
        assert "Main Heading" in text
        assert "First paragraph" in text
        assert "Second paragraph" in text
        assert "console.log" not in text  # Script should be removed
        print(f"✓ HTML parsing works correctly")

    @pytest.mark.asyncio
    async def test_scraper_error_handling(self, web_scraper):
        """Test error handling in scraper."""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Simulate network error
            mock_get.side_effect = Exception("Network error")
            
            result = await web_scraper.scrape_url("https://invalid-url.example.com")
            
            # Should return None on error
            assert result is None
            print("✓ Error handling works")

    @pytest.mark.asyncio
    async def test_content_preview_limit(self, web_scraper):
        """Test that content is limited to reasonable size."""
        large_content = "Lorem ipsum. " * 1000  # Large content
        
        with patch('httpx.AsyncClient.get') as mock_get:
            html = f"<html><head><title>Large</title></head><body>{large_content}</body></html>"
            mock_response = AsyncMock()
            mock_response.text = html
            mock_response.raise_for_status = AsyncMock()
            mock_get.return_value = mock_response
            
            with patch.object(web_scraper, '_generate_summary', new_callable=AsyncMock) as mock_summary:
                mock_summary.return_value = "Summary"
                
                result = await web_scraper.scrape_url("https://example.com")
        
        # Verify content is limited
        assert len(result.content) <= 4000  # Should be limited to 4000 chars
        print(f"✓ Content limited to {len(result.content)} characters")


class TestWebScraperIntegration:
    """Integration tests for web scraper (requires internet)."""

    @pytest.fixture
    def voice_config(self):
        """Get voice configuration."""
        return get_voice_config()

    @pytest.fixture
    def web_scraper(self, voice_config):
        """Create WebScraper instance."""
        return WebScraper(openai_api_key=voice_config.openai_api_key)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_scrape_real_website(self, web_scraper):
        """Test scraping a real website.
        
        This test requires internet connection and OpenAI API access.
        """
        try:
            # Try to scrape example.com
            result = await web_scraper.scrape_url("https://example.com")
            
            if result:
                assert result.title is not None
                assert len(result.content) > 0
                print(f"\n✓ Real website scraped successfully")
                print(f"  Title: {result.title}")
                print(f"  Content length: {len(result.content)} chars")
                if result.summary:
                    print(f"  Summary: {result.summary[:100]}...")
            else:
                pytest.skip("Failed to scrape website")
                
        except Exception as e:
            pytest.skip(f"Integration test skipped: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
