"""
Tests for Pulpoo API Integration

Tests the appointment creation and appointment management features.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import aiohttp

from agent_tools import AgentTools
from config import get_voice_config


class TestPulpooConnection:
    """Test Pulpoo API connection and appointment creation."""

    @pytest.fixture
    def voice_config(self):
        """Get voice configuration."""
        return get_voice_config()

    @pytest.fixture
    def agent_tools(self, voice_config):
        """Create AgentTools instance with test config."""
        return AgentTools(
            openai_api_key=voice_config.openai_api_key,
            deepgram_api_key=voice_config.deepgram_api_key,
            pulpoo_api_key=voice_config.pulpoo_api_key or "test_key",
        )

    @pytest.mark.asyncio
    async def test_pulpoo_api_key_configured(self, voice_config):
        """Test that Pulpoo API key is configured."""
        # Check if API key is set
        api_key = voice_config.pulpoo_api_key
        
        if api_key:
            assert len(api_key) > 0, "Pulpoo API key should not be empty"
            assert isinstance(api_key, str), "Pulpoo API key should be a string"
            print(f"✓ Pulpoo API key configured: {api_key[:10]}...")
        else:
            pytest.skip("Pulpoo API key not configured in .env")

    @pytest.mark.asyncio
    async def test_pulpoo_api_url_valid(self, voice_config):
        """Test that Pulpoo API URL is valid."""
        url = voice_config.pulpoo_api_url
        
        assert url is not None, "Pulpoo API URL should not be None"
        assert "pulpoo" in url.lower(), "URL should contain 'pulpoo'"
        assert "http" in url.lower(), "URL should be HTTP/HTTPS"
        print(f"✓ Pulpoo API URL valid: {url}")

    @pytest.mark.asyncio
    async def test_create_appointment_with_mock(self, agent_tools):
        """Test appointment creation with mocked HTTP response."""
        # Mock the aiohttp session
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Create mock response
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.json = AsyncMock(return_value={
                "id": "apt_12345",
                "status": "created",
                "customer_email": "test@example.com",
            })
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            
            # Mock the context manager
            mock_post.return_value.__aenter__.return_value = mock_response
            mock_post.return_value.__aexit__.return_value = None
            
            # Call the tool
            result = await agent_tools.create_appointment(
                user_name="John Doe",
                user_email="john@example.com",
                topic="Website Discussion",
            )
            
            # Verify result
            assert result["success"] is True, "Appointment creation should succeed"
            assert "appointment_id" in result, "Result should contain appointment_id"
            assert "scheduled_time" in result, "Result should contain scheduled_time"
            print(f"✓ Mock appointment created: {result}")

    @pytest.mark.asyncio
    async def test_appointment_creation_payload(self, agent_tools):
        """Test that appointment creation sends correct payload."""
        user_name = "Jane Smith"
        user_email = "jane@example.com"
        topic = "Product Demo"
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.json = AsyncMock(return_value={"id": "apt_test"})
            mock_post.return_value.__aenter__.return_value = mock_response
            mock_post.return_value.__aexit__.return_value = None
            
            await agent_tools.create_appointment(
                user_name=user_name,
                user_email=user_email,
                topic=topic,
            )
            
            # Verify the POST was called
            assert mock_post.called, "POST should be called"
            
            # Get the call arguments
            call_args = mock_post.call_args
            
            # Verify URL
            url = call_args[0][0] if call_args[0] else None
            assert "pulpoo" in url.lower(), "URL should contain pulpoo"
            
            # Verify headers
            headers = call_args[1].get("headers", {})
            assert "X-API-Key" in headers, "Headers should contain X-API-Key"
            assert headers["X-API-Key"] == agent_tools.pulpoo_api_key
            
            # Verify JSON payload
            json_payload = call_args[1].get("json", {})
            assert json_payload["title"] == f"Appointment: {topic}"
            assert user_name in json_payload["description"]
            assert user_email in json_payload["description"]
            
            print(f"✓ Appointment payload verified")
            print(f"  - URL: {url}")
            print(f"  - Headers: {headers}")
            print(f"  - Payload: {json_payload}")

    @pytest.mark.asyncio
    async def test_appointment_creation_error_handling(self, agent_tools):
        """Test error handling in appointment creation."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Simulate API error
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value="Bad Request")
            mock_post.return_value.__aenter__.return_value = mock_response
            mock_post.return_value.__aexit__.return_value = None
            
            result = await agent_tools.create_appointment(
                user_name="Test User",
                user_email="test@example.com",
                topic="Test Appointment",
            )
            
            # Verify error handling
            assert result["success"] is False, "Should return success=False on error"
            assert "error" in result, "Should contain error message"
            print(f"✓ Error handling works: {result}")

    @pytest.mark.asyncio
    async def test_appointment_without_api_key(self):
        """Test appointment creation when API key is missing."""
        # Create tools with no API key
        tools = AgentTools(
            openai_api_key="test",
            deepgram_api_key="test",
            pulpoo_api_key="",  # Empty key
        )
        
        result = await tools.create_appointment(
            user_name="Test User",
            user_email="test@example.com",
            topic="Test",
        )
        
        # Should fail gracefully
        assert result["success"] is False
        assert "not configured" in result["error"].lower()
        print(f"✓ Missing API key handled: {result}")

    @pytest.mark.asyncio
    async def test_get_available_slots(self, agent_tools):
        """Test getting available appointment slots."""
        result = await agent_tools.get_available_slots()
        
        # Verify structure
        assert result["success"] is True
        assert "available_slots" in result
        assert isinstance(result["available_slots"], list)
        assert len(result["available_slots"]) > 0
        
        # Verify slot structure
        slot = result["available_slots"][0]
        assert "slot_id" in slot
        assert "date_time" in slot
        assert "time_display" in slot
        
        print(f"✓ Available slots: {len(result['available_slots'])} slots")
        print(f"  First slot: {slot}")

    @pytest.mark.asyncio
    async def test_appointment_datetime_format(self, agent_tools):
        """Test that appointment datetime is in correct format."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.json = AsyncMock(return_value={"id": "apt_123"})
            mock_post.return_value.__aenter__.return_value = mock_response
            mock_post.return_value.__aexit__.return_value = None
            
            result = await agent_tools.create_appointment(
                user_name="Test User",
                user_email="test@example.com",
                topic="Test",
            )
            
            # Verify datetime format
            scheduled_time = result["scheduled_time"]
            
            # Should be ISO format
            try:
                dt = datetime.fromisoformat(scheduled_time)
                assert dt > datetime.utcnow(), "Appointment should be in the future"
                print(f"✓ Datetime format valid: {scheduled_time}")
            except ValueError:
                pytest.fail(f"Invalid datetime format: {scheduled_time}")

    @pytest.mark.asyncio
    async def test_appointment_duration(self, agent_tools):
        """Test appointment duration setting."""
        duration = 60  # 60 minutes
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.json = AsyncMock(return_value={"id": "apt_123"})
            mock_post.return_value.__aenter__.return_value = mock_response
            mock_post.return_value.__aexit__.return_value = None
            
            result = await agent_tools.create_appointment(
                user_name="Test User",
                user_email="test@example.com",
                topic="Test",
                duration_minutes=duration,
            )
            
            # Verify duration
            assert result["duration_minutes"] == duration
            print(f"✓ Duration set correctly: {result['duration_minutes']} minutes")


class TestPulpooIntegration:
    """Integration tests with actual Pulpoo API (requires valid credentials)."""

    @pytest.fixture
    def voice_config(self):
        """Get voice configuration."""
        return get_voice_config()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_appointment_creation(self, voice_config):
        """Test real appointment creation with Pulpoo API.
        
        This test requires valid Pulpoo API credentials.
        Skip if not configured.
        """
        if not voice_config.pulpoo_api_key:
            pytest.skip("Pulpoo API key not configured")
        
        tools = AgentTools(
            openai_api_key=voice_config.openai_api_key,
            deepgram_api_key=voice_config.deepgram_api_key,
            pulpoo_api_key=voice_config.pulpoo_api_key,
        )
        
        result = await tools.create_appointment(
            user_name="Test Integration User",
            user_email="integration@test.example.com",
            topic="Integration Test Appointment",
        )
        
        # Print result for debugging
        print(f"\n✓ Real Pulpoo Integration Test Result:")
        print(f"  Success: {result['success']}")
        if result['success']:
            print(f"  Appointment ID: {result['appointment_id']}")
            print(f"  Scheduled: {result['scheduled_time']}")
            print(f"  Message: {result['message']}")
        else:
            print(f"  Error: {result['error']}")


class TestPulpooErrorScenarios:
    """Test various error scenarios with Pulpoo API."""

    @pytest.fixture
    def agent_tools(self):
        """Create AgentTools instance."""
        return AgentTools(
            openai_api_key="test",
            deepgram_api_key="test",
            pulpoo_api_key="test_key",
        )

    @pytest.mark.asyncio
    async def test_pulpoo_timeout(self, agent_tools):
        """Test timeout handling."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Simulate timeout
            mock_post.side_effect = asyncio.TimeoutError("Request timeout")
            
            result = await agent_tools.create_appointment(
                user_name="Test User",
                user_email="test@example.com",
                topic="Test",
            )
            
            # Should handle timeout gracefully
            assert result["success"] is False
            print(f"✓ Timeout handled: {result['error']}")

    @pytest.mark.asyncio
    async def test_pulpoo_connection_error(self, agent_tools):
        """Test connection error handling."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Simulate connection error
            mock_post.side_effect = aiohttp.ClientConnectionError("Connection failed")
            
            result = await agent_tools.create_appointment(
                user_name="Test User",
                user_email="test@example.com",
                topic="Test",
            )
            
            # Should handle connection error gracefully
            assert result["success"] is False
            print(f"✓ Connection error handled: {result['error']}")

    @pytest.mark.asyncio
    async def test_pulpoo_invalid_response(self, agent_tools):
        """Test invalid API response handling."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500  # Server error
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            mock_post.return_value.__aenter__.return_value = mock_response
            mock_post.return_value.__aexit__.return_value = None
            
            result = await agent_tools.create_appointment(
                user_name="Test User",
                user_email="test@example.com",
                topic="Test",
            )
            
            # Should handle server error
            assert result["success"] is False
            assert "500" in result["error"]
            print(f"✓ Server error handled: {result['error']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
