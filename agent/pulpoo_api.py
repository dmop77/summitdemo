"""
FastAPI service to proxy Pulpoo task creation.

Exposes a POST /pulpoo/tasks endpoint that accepts title, description,
deadline (ISO 8601), and importance, and uses the PULPOO_API_KEY from env.
"""

import os
import logging
from typing import Optional, List, Union
from datetime import datetime, timedelta

import pytz
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv(".env")

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

PULPOO_API_KEY = os.getenv("PULPOO_API_KEY")

app = FastAPI(title="Pulpoo Proxy API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateTaskRequest(BaseModel):
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    deadline: Optional[str] = Field(None, description="Deadline in ISO 8601 (UTC)")
    importance: Optional[str] = Field("HIGH", description="LOW, MEDIUM, HIGH")
    assigned_to_email: Optional[Union[str, List[str]]] = Field(
        None,
        description="Email of the assignee (string) or list; first will be used",
    )


class CreateTaskResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.post("/pulpoo/tasks", response_model=CreateTaskResponse)
def create_pulpoo_task(req: CreateTaskRequest) -> CreateTaskResponse:
    if not PULPOO_API_KEY:
        raise HTTPException(status_code=500, detail="PULPOO_API_KEY not configured")

    importance = (req.importance or "HIGH").upper()
    if importance not in {"LOW", "MEDIUM", "HIGH"}:
        importance = "HIGH"

    # Default deadline +24h if not provided
    deadline = req.deadline
    if not deadline:
        deadline_dt = datetime.now(pytz.UTC) + timedelta(hours=24)
        deadline = deadline_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Coerce assigned_to_email to a single string for Pulpoo API
    assigned_email: Optional[str] = None
    if isinstance(req.assigned_to_email, list):
        assigned_email = req.assigned_to_email[0] if req.assigned_to_email else None
    else:
        assigned_email = req.assigned_to_email

    payload = {
        "title": req.title,
        "description": req.description or f"Task created via proxy: {req.title}",
        "assigned_to_email": assigned_email,
        "deadline": deadline,
        "importance": importance,
    }

    headers = {
        "X-API-Key": PULPOO_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://api.pulpoo.com/v1/external/tasks/create",
            headers=headers,
            json=payload,
            timeout=10,
        )

        if resp.status_code in (200, 201):
            return CreateTaskResponse(success=True, data=resp.json())
        else:
            # Surface Pulpoo error message if present
            try:
                err = resp.json()
            except Exception:
                err = {"message": resp.text}
            logger.error("Pulpoo API error %s: %s", resp.status_code, err)
            return CreateTaskResponse(success=False, error=f"{resp.status_code}: {err}")

    except requests.exceptions.Timeout:
        return CreateTaskResponse(success=False, error="Timeout connecting to Pulpoo")
    except requests.exceptions.ConnectionError:
        return CreateTaskResponse(success=False, error="Connection error to Pulpoo")
    except Exception as e:
        return CreateTaskResponse(success=False, error=f"Unexpected error: {str(e)}")


