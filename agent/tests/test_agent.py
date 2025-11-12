"""
Tests for the simplified, efficient agent.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agent_tools import AppointmentScheduler


@pytest.mark.asyncio
async def test_appointment_scheduler_initialization():
    """Test scheduler initializes correctly."""
    scheduler = AppointmentScheduler(
        openai_api_key="test_key",
        pulpoo_api_key="test_pulpoo",
    )
    assert scheduler.openai_api_key == "test_key"
    assert scheduler.pulpoo_api_key == "test_pulpoo"


@pytest.mark.asyncio
async def test_appointment_scheduler_missing_api_key():
    """Test scheduler handles missing API key."""
    scheduler = AppointmentScheduler(
        openai_api_key="test_key",
        pulpoo_api_key="",
    )
    result = await scheduler.schedule_appointment(
        user_name="John Doe",
        user_email="john@example.com",
        appointment_topic="Test",
        preferred_date="2025-11-15T14:30:00",
    )
    assert result["success"] is False
    assert "API key" in result["error"]


@pytest.mark.asyncio
async def test_appointment_scheduler_invalid_date():
    """Test scheduler handles invalid date."""
    scheduler = AppointmentScheduler(
        openai_api_key="test_key",
        pulpoo_api_key="test_pulpoo",
    )
    result = await scheduler.schedule_appointment(
        user_name="John Doe",
        user_email="john@example.com",
        appointment_topic="Test",
        preferred_date="invalid-date",
    )
    assert result["success"] is False
    assert "Invalid" in result["error"]


@pytest.mark.asyncio
async def test_appointment_scheduler_successful_creation():
    """Test successful appointment creation with mock."""
    scheduler = AppointmentScheduler(
        openai_api_key="test_key",
        pulpoo_api_key="test_pulpoo",
    )
    
    mock_response = AsyncMock()
    mock_response.status = 201
    mock_response.json = AsyncMock(return_value={"id": "apt_12345"})
    
    mock_post_cm = AsyncMock()
    mock_post_cm.__aenter__.return_value = mock_response
    mock_post_cm.__aexit__.return_value = None
    
    with patch('agent_tools.aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_cm
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        result = await scheduler.schedule_appointment(
            user_name="John Doe",
            user_email="john@example.com",
            appointment_topic="Test",
            preferred_date="2025-11-15T14:30:00",
            summary_notes="Test summary",
        )
        
        assert result["success"] is True
        assert result["appointment_id"] == "apt_12345"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
