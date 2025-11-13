"""Tests for scraped content operations in the database."""

import pytest
import uuid


@pytest.mark.asyncio
async def test_save_scraped_content(db_client, test_user_email, test_user_name, test_website_url):
    """Test saving scraped website content."""
    # Create user and session
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    session_id = str(uuid.uuid4())
    session = await db_client.create_session(
        user_id=user["id"],
        session_id=session_id
    )

    # Save scraped content
    content = await db_client.save_scraped_content(
        user_id=user["id"],
        session_id=session["id"],
        url="https://example.com",
        title="Example Website",
        summary="A test website for examples",
        content="This is the full content of the website..."
    )

    assert content is not None
    assert content["url"] == "https://example.com"
    assert content["title"] == "Example Website"
    assert content["summary"] == "A test website for examples"
    assert content["user_id"] == user["id"]


@pytest.mark.asyncio
async def test_get_scraped_content(db_client, test_user_email, test_user_name, test_website_url):
    """Test retrieving scraped content for a user."""
    # Create user and session
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    session_id = str(uuid.uuid4())
    session = await db_client.create_session(
        user_id=user["id"],
        session_id=session_id
    )

    # Save multiple scraped contents
    urls = [
        ("https://example1.com", "Site 1"),
        ("https://example2.com", "Site 2"),
        ("https://example3.com", "Site 3"),
    ]

    for url, title in urls:
        await db_client.save_scraped_content(
            user_id=user["id"],
            session_id=session["id"],
            url=url,
            title=title,
            summary=f"Summary for {title}",
            content=f"Content for {title}"
        )

    # Get scraped content
    contents = await db_client.get_scraped_content(user["id"], limit=5)

    assert len(contents) >= 3
    assert contents[0]["user_id"] == user["id"]


@pytest.mark.asyncio
async def test_scraped_content_with_hash(db_client, test_user_email, test_user_name, test_website_url):
    """Test saving scraped content with content hash."""
    # Create user and session
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    session_id = str(uuid.uuid4())
    session = await db_client.create_session(
        user_id=user["id"],
        session_id=session_id
    )

    # Save with hash
    content_hash = "abc123def456"
    content = await db_client.save_scraped_content(
        user_id=user["id"],
        session_id=session["id"],
        url="https://example.com",
        title="Example",
        summary="Summary",
        content="Content",
        content_hash=content_hash
    )

    assert content["content_hash"] == content_hash


@pytest.mark.asyncio
async def test_scraped_content_limit(db_client, test_user_email, test_user_name, test_website_url):
    """Test that scraped content limit is respected."""
    # Create user and session
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    session_id = str(uuid.uuid4())
    session = await db_client.create_session(
        user_id=user["id"],
        session_id=session_id
    )

    # Save 10 items
    for i in range(10):
        await db_client.save_scraped_content(
            user_id=user["id"],
            session_id=session["id"],
            url=f"https://example{i}.com",
            title=f"Site {i}",
            summary=f"Summary {i}",
            content=f"Content {i}"
        )

    # Get with limit 3
    contents = await db_client.get_scraped_content(user["id"], limit=3)

    assert len(contents) <= 3
