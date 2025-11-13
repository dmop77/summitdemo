"""Pytest configuration and fixtures for Supabase integration tests."""

import os
import pytest
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def supabase_url():
    """Get Supabase URL from environment."""
    return os.getenv("SUPABASE_URL")


@pytest.fixture
def supabase_key():
    """Get Supabase service role key from environment."""
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY")


@pytest.fixture
def db_client(supabase_url, supabase_key):
    """Create a Supabase client instance."""
    if not supabase_url or not supabase_key:
        pytest.skip("Supabase credentials not configured")

    from agent.db_client import SupabaseClient
    return SupabaseClient(supabase_url, supabase_key)


@pytest.fixture
def test_user_email():
    """Test user email for fixtures."""
    return f"test-{os.urandom(4).hex()}@example.com"


@pytest.fixture
def test_user_name():
    """Test user name for fixtures."""
    return "Test User"


@pytest.fixture
def test_website_url():
    """Test website URL for fixtures."""
    return "https://example.com"
