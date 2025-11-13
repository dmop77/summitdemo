"""Tests for appointment operations in the database."""

import pytest
import uuid
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_create_appointment(db_client, test_user_email, test_user_name, test_website_url):
    """Test creating an appointment."""
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
        topic="Website Consultation",
        preferred_date=future_date.isoformat(),
        summary_notes="Discussed integration needs"
    )

    assert appointment is not None
    assert appointment["topic"] == "Website Consultation"
    assert appointment["status"] == "scheduled"
    assert appointment["user_id"] == user["id"]


@pytest.mark.asyncio
async def test_get_appointments(db_client, test_user_email, test_user_name, test_website_url):
    """Test retrieving appointments for a user."""
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

    # Create multiple appointments
    future_date = datetime.utcnow() + timedelta(days=5)
    for i in range(3):
        await db_client.create_appointment(
            user_id=user["id"],
            session_id=session["id"],
            topic=f"Meeting {i}",
            preferred_date=future_date.isoformat()
        )

    # Get appointments
    appointments = await db_client.get_appointments(user["id"])

    assert len(appointments) >= 3
    assert appointments[0]["user_id"] == user["id"]


@pytest.mark.asyncio
async def test_get_appointments_by_status(db_client, test_user_email, test_user_name, test_website_url):
    """Test retrieving appointments filtered by status."""
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

    # Get scheduled appointments
    scheduled = await db_client.get_appointments(user["id"], status="scheduled")

    assert len(scheduled) >= 1
    assert all(a["status"] == "scheduled" for a in scheduled)


@pytest.mark.asyncio
async def test_update_appointment(db_client, test_user_email, test_user_name, test_website_url):
    """Test updating an appointment."""
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
        topic="Original Topic",
        preferred_date=future_date.isoformat()
    )

    # Update appointment
    updated = await db_client.update_appointment(
        appointment["id"],
        status="completed",
        summary_notes="Appointment completed successfully"
    )

    assert updated["status"] == "completed"
    assert updated["summary_notes"] == "Appointment completed successfully"


@pytest.mark.asyncio
async def test_appointment_with_external_id(db_client, test_user_email, test_user_name, test_website_url):
    """Test creating appointment with external ID (e.g., from Pulpoo)."""
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

    # Create appointment with external ID
    future_date = datetime.utcnow() + timedelta(days=5)
    external_id = "pulpoo-12345"
    appointment = await db_client.create_appointment(
        user_id=user["id"],
        session_id=session["id"],
        topic="External Appointment",
        preferred_date=future_date.isoformat(),
        external_id=external_id
    )

    assert appointment["external_id"] == external_id


@pytest.mark.asyncio
async def test_appointment_with_pulpoo_response(db_client, test_user_email, test_user_name, test_website_url):
    """Test storing Pulpoo API response with appointment."""
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

    # Create appointment with Pulpoo response
    future_date = datetime.utcnow() + timedelta(days=5)
    pulpoo_response = {
        "task_id": "task-123",
        "status": "created",
        "timestamp": datetime.utcnow().isoformat()
    }

    appointment = await db_client.create_appointment(
        user_id=user["id"],
        session_id=session["id"],
        topic="Pulpoo Integration",
        preferred_date=future_date.isoformat(),
        pulpoo_response=pulpoo_response
    )

    assert appointment["pulpoo_response"] is not None
    assert appointment["pulpoo_response"]["task_id"] == "task-123"
