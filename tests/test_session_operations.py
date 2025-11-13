"""Tests for session operations in the database."""

import pytest
import uuid


@pytest.mark.asyncio
async def test_create_session(db_client, test_user_email, test_user_name, test_website_url):
    """Test creating a new session."""
    # Create user first
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    session_id = str(uuid.uuid4())
    session = await db_client.create_session(
        user_id=user["id"],
        session_id=session_id,
        website_summary="Test summary"
    )

    assert session is not None
    assert session["user_id"] == user["id"]
    assert session["session_id"] == session_id
    assert session["status"] == "active"


@pytest.mark.asyncio
async def test_get_session(db_client, test_user_email, test_user_name, test_website_url):
    """Test retrieving a session."""
    # Create user and session
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    session_id = str(uuid.uuid4())
    created_session = await db_client.create_session(
        user_id=user["id"],
        session_id=session_id,
        website_summary="Test summary"
    )

    # Retrieve session
    retrieved_session = await db_client.get_session(session_id)

    assert retrieved_session is not None
    assert retrieved_session["session_id"] == session_id
    assert retrieved_session["user_id"] == user["id"]


@pytest.mark.asyncio
async def test_update_session_status(db_client, test_user_email, test_user_name, test_website_url):
    """Test updating session status."""
    # Create user and session
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    session_id = str(uuid.uuid4())
    await db_client.create_session(
        user_id=user["id"],
        session_id=session_id,
        website_summary="Test summary"
    )

    # Update status
    await db_client.update_session_status(session_id, "completed")

    # Verify
    session = await db_client.get_session(session_id)
    assert session["status"] == "completed"


@pytest.mark.asyncio
async def test_session_status_validation(db_client, test_user_email, test_user_name, test_website_url):
    """Test that session status is validated."""
    # Create user
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    session_id = str(uuid.uuid4())
    await db_client.create_session(
        user_id=user["id"],
        session_id=session_id
    )

    # Valid statuses: 'active', 'completed', 'abandoned'
    for status in ['active', 'completed', 'abandoned']:
        await db_client.update_session_status(session_id, status)
        session = await db_client.get_session(session_id)
        assert session["status"] == status
