"""
Pytest configuration and shared fixtures.

Provides:
- Configuration for all tests
- Shared fixtures for common test setup
- Mock data and helpers
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta


@pytest.fixture
def mock_aiohttp_response():
    """Create a mock aiohttp response."""
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock()
    response.text = AsyncMock()
    return response


@pytest.fixture
def sample_appointment_data():
    """Sample appointment data for testing."""
    tomorrow = datetime.utcnow() + timedelta(days=1)
    return {
        "user_name": "John Doe",
        "user_email": "john@example.com",
        "topic": "Website Discussion",
        "preferred_date": tomorrow.isoformat(),
        "duration_minutes": 30,
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "website_url": "https://example.com",
    }


@pytest.fixture
def sample_html_content():
    """Sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Example Company</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <h1>Welcome to Example Company</h1>
        <p>We provide innovative solutions for your business.</p>
        <p>Our services include consulting, development, and support.</p>
        <section>
            <h2>About Us</h2>
            <p>Founded in 2010, we have served over 500 clients worldwide.</p>
        </section>
        <footer>
            <p>&copy; 2025 Example Company. All rights reserved.</p>
        </footer>
    </body>
    </html>
    """


@pytest.fixture
def sample_api_response():
    """Sample Pulpoo API response."""
    return {
        "id": "apt_12345",
        "title": "Appointment: Website Discussion",
        "status": "created",
        "customer_email": "john@example.com",
        "customer_name": "John Doe",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_slots_response():
    """Sample available slots response."""
    slots = []
    start_date = datetime.utcnow().replace(hour=9, minute=0, second=0)
    
    for day in range(7):
        for hour in [9, 11, 14, 16]:
            slot_time = start_date + timedelta(days=day, hours=hour)
            slots.append({
                "slot_id": f"slot_{len(slots)}",
                "date_time": slot_time.isoformat(),
                "time_display": slot_time.strftime("%A, %B %d at %I:%M %p"),
            })
    
    return {
        "success": True,
        "available_slots": slots[:10],
        "message": f"Found {len(slots)} available slots",
    }


@pytest.fixture
def mock_config():
    """Mock configuration object."""
    config = MagicMock()
    config.deepgram_api_key = "test_deepgram_key"
    config.openai_api_key = "test_openai_key"
    config.pulpoo_api_key = "test_pulpoo_key"
    config.pulpoo_api_url = "https://api.pulpoo.com/v1/external/tasks/create"
    config.openai_model = "gpt-4o-mini"
    config.deepgram_model = "nova-3"
    config.host = "0.0.0.0"
    config.port = 8084
    return config


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (requires external APIs)"
    )
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


# Async test configuration
pytest_plugins = ('pytest_asyncio',)


def pytest_collection_modifyitems(config, items):
    """Automatically add asyncio marker to async tests."""
    for item in items:
        if "asyncio" in item.keywords:
            continue
        if item.get_closest_marker("asyncio"):
            item.add_marker(pytest.mark.asyncio)
