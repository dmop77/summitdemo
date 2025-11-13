"""Integration tests for complete workflow scenarios."""

import pytest
import uuid
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_complete_conversation_workflow(db_client, test_user_email, test_user_name, test_website_url):
    """Test a complete conversation workflow: user -> session -> messages -> appointment."""

    # 1. Create user
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )
    assert user is not None
    user_id = user["id"]

    # 2. Create session
    session_id = str(uuid.uuid4())
    session = await db_client.create_session(
        user_id=user_id,
        session_id=session_id,
        website_summary="Website is about software consulting"
    )
    assert session is not None
    session_db_id = session["id"]

    # 3. Save scraped content
    content = await db_client.save_scraped_content(
        user_id=user_id,
        session_id=session_db_id,
        url=test_website_url,
        title="Test Website",
        summary="Website about software consulting",
        content="Detailed content about the website..."
    )
    assert content is not None

    # 4. Simulate conversation with messages
    messages = [
        ("user", "Hello, can you help me?"),
        ("agent", "Of course! I can help with consulting services."),
        ("user", "Great! I need to discuss a project."),
        ("agent", "Let's schedule a call to discuss the details."),
    ]

    for sender, text in messages:
        msg = await db_client.save_message(
            session_id=session_db_id,
            user_id=user_id,
            sender=sender,
            message_text=text
        )
        assert msg is not None

    # 5. Create appointment
    future_date = datetime.utcnow() + timedelta(days=7)
    appointment = await db_client.create_appointment(
        user_id=user_id,
        session_id=session_db_id,
        topic="Project Consultation",
        preferred_date=future_date.isoformat(),
        summary_notes="User wants to discuss a new software project"
    )
    assert appointment is not None

    # 6. Verify complete workflow
    history = await db_client.get_conversation_history(session_db_id)
    assert len(history) == 4

    appointments = await db_client.get_appointments(user_id)
    assert len(appointments) >= 1

    stats = await db_client.get_user_stats(user_id)
    assert stats["sessions_count"] >= 1
    assert stats["messages_count"] >= 4
    assert stats["appointments_count"] >= 1


@pytest.mark.asyncio
async def test_multiple_sessions_same_user(db_client, test_user_email, test_user_name, test_website_url):
    """Test that a user can have multiple sessions."""

    # Create user
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    # Create multiple sessions
    sessions = []
    for i in range(3):
        session_id = str(uuid.uuid4())
        session = await db_client.create_session(
            user_id=user["id"],
            session_id=session_id,
            website_summary=f"Session {i} summary"
        )
        sessions.append(session)

        # Add messages to each session
        await db_client.save_message(
            session_id=session["id"],
            user_id=user["id"],
            sender="user",
            message_text=f"Session {i} message"
        )

    # Verify stats
    stats = await db_client.get_user_stats(user["id"])
    assert stats["sessions_count"] >= 3
    assert stats["messages_count"] >= 3


@pytest.mark.asyncio
async def test_session_status_lifecycle(db_client, test_user_email, test_user_name, test_website_url):
    """Test the lifecycle of a session status: active -> completed."""

    # Create user
    user = await db_client.get_or_create_user(
        email=test_user_email,
        name=test_user_name,
        website_url=test_website_url
    )

    # Create session (default: active)
    session_id = str(uuid.uuid4())
    session = await db_client.create_session(
        user_id=user["id"],
        session_id=session_id
    )

    assert session["status"] == "active"

    # Add some activity
    await db_client.save_message(
        session_id=session["id"],
        user_id=user["id"],
        sender="user",
        message_text="Test message"
    )

    # Complete session
    await db_client.update_session_status(session_id, "completed")

    # Verify
    completed_session = await db_client.get_session(session_id)
    assert completed_session["status"] == "completed"


@pytest.mark.asyncio
async def test_appointment_status_lifecycle(db_client, test_user_email, test_user_name, test_website_url):
    """Test the lifecycle of an appointment status."""

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

    # Create appointment
    future_date = datetime.utcnow() + timedelta(days=5)
    appointment = await db_client.create_appointment(
        user_id=user["id"],
        session_id=session["id"],
        topic="Test Appointment",
        preferred_date=future_date.isoformat()
    )

    assert appointment["status"] == "scheduled"

    # Update to completed
    updated = await db_client.update_appointment(
        appointment["id"],
        status="completed"
    )
    assert updated["status"] == "completed"

    # Update to no-show
    updated2 = await db_client.update_appointment(
        appointment["id"],
        status="no-show"
    )
    assert updated2["status"] == "no-show"
