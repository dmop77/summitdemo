"""Tests for user operations in the database."""

import pytest


@pytest.mark.asyncio
async def test_create_user(db_client, test_user_email, test_user_name, test_website_url):
    """Test creating a new user."""
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    assert user is not None
    assert user["email"] == test_user_email
    assert user["name"] == test_user_name
    assert user["website_url"] == test_website_url
    assert "id" in user


@pytest.mark.asyncio
async def test_get_existing_user(db_client, test_user_email, test_user_name, test_website_url):
    """Test retrieving an existing user."""
    # Create user first
    created_user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    # Get the same user
    retrieved_user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    assert retrieved_user["id"] == created_user["id"]
    assert retrieved_user["email"] == test_user_email


@pytest.mark.asyncio
async def test_user_email_unique(db_client, test_user_email, test_user_name, test_website_url):
    """Test that user email is unique."""
    # Create first user
    user1 = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    # Try to create another user with same email (should return existing)
    user2 = await db_client.get_or_create_user(
        email=test_user_email,
        name="Different Name",
        website_url="https://different.com"
    )

    assert user1["id"] == user2["id"]


@pytest.mark.asyncio
async def test_get_user_stats(db_client, test_user_email, test_user_name, test_website_url):
    """Test getting user statistics."""
    # Create user
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    # Get stats
    stats = await db_client.get_user_stats(user["id"])

    assert stats is not None
    assert "sessions_count" in stats
    assert "messages_count" in stats
    assert "appointments_count" in stats
    assert stats["sessions_count"] >= 0
