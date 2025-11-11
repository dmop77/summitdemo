Sure — here’s the complete Markdown file as a single copy-ready document you can paste directly into your repo.

⸻


# 🧠 LiveKit Voice Agent Enhancement Plan

## Overview
This document outlines the plan to extend the existing **LiveKit voice agent** system by integrating:
1. A **web scraping and Supabase ingestion pipeline**.  
2. An **enhanced conversational workflow** that includes a Pulpo-based scheduling flow with rescheduling logic.  
3. A **verification layer using the Archon MCP server** (located inside Claude’s codebase) to validate agent behavior and LiveKit documentation references.

The objective is to allow a user to input a website link, automatically scrape it, store embeddings in Supabase, and enable the voice agent to:
- Discuss the scraped content intelligently.  
- Greet the user using Cartesia voice (English).  
- Collect user info (name, email, website link).  
- Create and **reschedule** appointments through Pulpo.  

> ⚠️ **Note:**  
> The base `.env` configuration already exists.  
> We will only **extend it** with additional keys for Supabase and web scraping — not create a new `.env.example` file.

---

## 🧩 System Components

### 1. LiveKit Voice Agent (Existing)
- **Already functional.**
- Uses:
  - **STT:** Deepgram  
  - **LLM:** OpenAI  
  - **TTS:** Cartesia  
- Fully capable of conversation flow and Pulpo API calls.

### 2. Web Scraping and Supabase Integration (New)
- The user inputs a **website link**.  
- A **Python scraper** fetches key text content and produces a **short summary + embedding**.  
- The embedding is stored in **Supabase**, linked to the user’s record (email, name, URL).

#### Workflow:
1. User provides `name`, `email`, and `link` through the frontend form.  
2. Backend runs the Python scraper and creates an embedding using the existing OpenAI model.  
3. Store results in Supabase table:
   ```sql
   Table: scraped_links
   Columns:
     - id (uuid)
     - user_name (text)
     - user_email (text)
     - url (text)
     - summary (text)
     - embedding (vector)
     - created_at (timestamp)

	4.	The embedding is later retrieved when the voice agent interacts with the user.

⚠️ Note:
Supabase and the web scraping module are not yet integrated.
This step will add both functionalities on top of the existing backend.

⸻

🗣️ Voice Interaction Flow

Agent Goals:
	1.	Greet the user in English using Cartesia (friendly + concise tone).
	2.	Reference scraped topic: Briefly summarize the subject from the embedded content.
	3.	Schedule a call via Pulpo using user’s email and name.
	4.	Showcase rescheduling logic:
	•	Reject the first proposed appointment (simulate unavailability).
	•	Check available times via Pulpo.
	•	Offer a second available slot and confirm it.

Example Flow:

Agent: Hi {name}, I just read the page you shared about {topic_summary}.
Agent: It looks interesting — I’d love to discuss it with you. Let’s find a time for a quick call.

(User chooses a time)

Agent: Looks like that time isn’t available. Let me check other options.
Agent: How about {alternative_time}? Should I book that for you?

(User confirms)

Agent: Great! I’ve scheduled your call in Pulpo and added your notes about {topic_summary}.


⸻

🧠 Archon MCP Verification
	•	The Archon MCP server is not inside this repository — it is part of Claude’s code environment.
	•	It should be used to:
	1.	Review LiveKit documentation to ensure the agent correctly handles session flow, transcription, and streaming.
	2.	Verify that Pulpo API calls are made correctly and that rescheduling logic works as expected.
	3.	Optionally cross-check any future integrations (e.g., Supabase SDK usage, web scraping setup).

✅ Goal: The Archon MCP acts as an intelligent reviewer to confirm that LiveKit and Pulpo integrations align with best practices and current documentation.

⸻

⚙️ Environment Variables

Add the following keys on top of the existing .env file — do not replace it.

# Supabase
SUPABASE_URL=<your_supabase_project_url>
SUPABASE_KEY=<your_supabase_api_key>

# Web Scraper
SCRAPER_ENDPOINT=<local_or_remote_scraper_url>

The rest of your .env (LiveKit, OpenAI, Deepgram, Cartesia, Pulpo, etc.) remains unchanged.

⸻

🧱 Reusability Setup

To make the project portable and shareable:
	•	Ensure environment variables are loaded from .env — no hardcoded credentials.
	•	Database credentials (Supabase) can be shared with trusted collaborators.
	•	The system should run locally or remotely with the same flow:
	1.	User inputs data (name, email, link).
	2.	Scraper runs → Supabase updated.
	3.	Voice agent engages → Pulpo scheduling occurs.
	4.	Archon MCP verifies documentation and consistency.

⸻

🧩 Architecture Overview

        ┌──────────────────────┐
        │        User          │
        │ (name, email, link)  │
        └──────────┬───────────┘
                   │
                   ▼
          ┌────────────────┐
          │  Web Scraper   │
          │ (Python script)│
          └───────┬────────┘
                  │
                  ▼
          ┌────────────────┐
          │   Supabase DB  │
          │ embeddings +   │
          │ summaries      │
          └───────┬────────┘
                  │
                  ▼
          ┌────────────────┐
          │  LiveKit Agent │
          │ Deepgram STT   │
          │ OpenAI LLM     │
          │ Cartesia TTS   │
          └───────┬────────┘
                  │
                  ▼
          ┌────────────────┐
          │    Pulpo API   │
          │ Appointment &  │
          │ Rescheduling   │
          └───────┬────────┘
                 



⸻

✅ Next Steps
	1.	Integrate Supabase with schema described above.
	2.	Connect the web scraping Python script to the backend ingestion pipeline.
	3.	Test the voice agent flow end-to-end with Pulpo scheduling and rescheduling logic.
	4.	Run Archon MCP validation on LiveKit + Pulpo interaction flow.
	5.	Ensure the final system runs locally and can be cloned by another user with minimal config updates.

⸻

🧾 Summary

Component	Status	Description
LiveKit Agent	✅ Existing	Uses Deepgram (STT), OpenAI (LLM), Cartesia (TTS)
Pulpo Integration	✅ Existing	Will now include rescheduling demo
Web Scraper	⚙️ New	Scrapes page + creates summary + embedding
Supabase	⚙️ New	Stores scraped data and embeddings
Archon MCP	🔍 External	Used for verifying LiveKit and integration consistency
.env	🔧 Extend Only	Add Supabase + Scraper keys; do not replace existing


