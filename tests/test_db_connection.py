"""Tests for database connection and health checks."""

import pytest


@pytest.mark.asyncio
async def test_database_connection(db_client):
    """Test that database connection is established."""
    assert db_client is not None
    assert db_client.client is not None


@pytest.mark.asyncio
async def test_health_check(db_client):
    """Test database health check."""
    health = await db_client.health_check()
    assert health is True, "Database health check failed"


@pytest.mark.asyncio
async def test_users_table_exists(db_client):
    """Test that users table exists and is accessible."""
    try:
        response = db_client.client.table("users").select("count").limit(1).execute()
        assert response is not None
        assert hasattr(response, 'data') or hasattr(response, 'count')
    except Exception as e:
        pytest.fail(f"Failed to access users table: {e}")


@pytest.mark.asyncio
async def test_sessions_table_exists(db_client):
    """Test that sessions table exists and is accessible."""
    try:
        response = db_client.client.table("sessions").select("count").limit(1).execute()
        assert response is not None
    except Exception as e:
        pytest.fail(f"Failed to access sessions table: {e}")


@pytest.mark.asyncio
async def test_conversation_messages_table_exists(db_client):
    """Test that conversation_messages table exists and is accessible."""
    try:
        response = db_client.client.table("conversation_messages").select("count").limit(1).execute()
        assert response is not None
    except Exception as e:
        pytest.fail(f"Failed to access conversation_messages table: {e}")


@pytest.mark.asyncio
async def test_appointments_table_exists(db_client):
    """Test that appointments table exists and is accessible."""
    try:
        response = db_client.client.table("appointments").select("count").limit(1).execute()
        assert response is not None
    except Exception as e:
        pytest.fail(f"Failed to access appointments table: {e}")


@pytest.mark.asyncio
async def test_scraped_content_table_exists(db_client):
    """Test that scraped_content table exists and is accessible."""
    try:
        response = db_client.client.table("scraped_content").select("count").limit(1).execute()
        assert response is not None
    except Exception as e:
        pytest.fail(f"Failed to access scraped_content table: {e}")
