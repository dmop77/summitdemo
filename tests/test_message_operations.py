"""Tests for conversation message operations in the database."""

import pytest
import uuid


@pytest.mark.asyncio
async def test_save_message(db_client, test_user_email, test_user_name, test_website_url):
    """Test saving a conversation message."""
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

    # Save message
    message = await db_client.save_message(
        session_id=session["id"],
        user_id=user["id"],
        sender="user",
        message_text="Hello, how can you help?",
        transcript="Hello, how can you help?"
    )

    assert message is not None
    assert message["sender"] == "user"
    assert message["message_text"] == "Hello, how can you help?"
    assert message["user_id"] == user["id"]


@pytest.mark.asyncio
async def test_save_user_and_agent_messages(db_client, test_user_email, test_user_name, test_website_url):
    """Test saving both user and agent messages."""
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

    # Save user message
    user_msg = await db_client.save_message(
        session_id=session["id"],
        user_id=user["id"],
        sender="user",
        message_text="What can you do?"
    )

    # Save agent message
    agent_msg = await db_client.save_message(
        session_id=session["id"],
        user_id=user["id"],
        sender="agent",
        message_text="I can help schedule appointments."
    )

    assert user_msg["sender"] == "user"
    assert agent_msg["sender"] == "agent"
    assert user_msg["message_text"] != agent_msg["message_text"]


@pytest.mark.asyncio
async def test_get_conversation_history(db_client, test_user_email, test_user_name, test_website_url):
    """Test retrieving conversation history."""
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

    # Save multiple messages
    messages_to_save = [
        ("user", "Hello"),
        ("agent", "Hi there!"),
        ("user", "Can you help?"),
        ("agent", "Of course!")
    ]

    for sender, text in messages_to_save:
        await db_client.save_message(
            session_id=session["id"],
            user_id=user["id"],
            sender=sender,
            message_text=text
        )

    # Retrieve history
    history = await db_client.get_conversation_history(session["id"])

    assert len(history) == 4
    assert history[0]["sender"] == "user"
    assert history[0]["message_text"] == "Hello"
    assert history[-1]["sender"] == "agent"
    assert history[-1]["message_text"] == "Of course!"


@pytest.mark.asyncio
async def test_conversation_history_ordering(db_client, test_user_email, test_user_name, test_website_url):
    """Test that conversation history is ordered chronologically."""
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

    # Save messages
    for i in range(3):
        await db_client.save_message(
            session_id=session["id"],
            user_id=user["id"],
            sender="user",
            message_text=f"Message {i}"
        )

    # Get history with limit
    history = await db_client.get_conversation_history(session["id"], limit=2)

    assert len(history) == 2
    assert history[0]["message_text"] == "Message 1"  # Second message
    assert history[1]["message_text"] == "Message 2"  # Third message
